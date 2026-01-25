use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::io::Cursor;
use std::ops::ControlFlow;

use pgn_reader::{RawComment, RawTag, Reader, SanPlus, Visitor};
use shakmaty::fen::Fen;
use shakmaty::uci::UciMove;
use shakmaty::{CastlingMode, Chess, Color, EnPassantMode, Position};

#[derive(Debug, Clone)]
struct PositionRecord {
    game_id: String,
    user: String,
    source: String,
    fen: String,
    ply: u32,
    move_number: u32,
    side_to_move: String,
    uci: String,
    san: String,
    clock_seconds: Option<f64>,
}

#[derive(Default, Debug)]
struct TagsState {
    white: Option<String>,
    black: Option<String>,
    site: Option<String>,
    fen: Option<Chess>,
}

#[derive(Debug)]
struct MovetextState {
    position: Chess,
    positions: Vec<PositionRecord>,
    user_color: Option<Color>,
    user: String,
    source: String,
    game_id: String,
    ply: u32,
    last_position_index: Option<usize>,
}

struct ExtractVisitor {
    user: String,
    source: String,
    game_id_override: Option<String>,
}

impl ExtractVisitor {
    fn new(user: &str, source: &str, game_id: Option<&str>) -> Self {
        Self {
            user: user.to_string(),
            source: source.to_string(),
            game_id_override: game_id.map(|value| value.to_string()),
        }
    }
}

impl Visitor for ExtractVisitor {
    type Tags = TagsState;
    type Movetext = MovetextState;
    type Output = Result<Vec<PositionRecord>, String>;

    fn begin_tags(&mut self) -> ControlFlow<Self::Output, Self::Tags> {
        ControlFlow::Continue(TagsState::default())
    }

    fn tag(
        &mut self,
        tags: &mut Self::Tags,
        name: &[u8],
        value: RawTag<'_>,
    ) -> ControlFlow<Self::Output> {
        let tag_value = String::from_utf8_lossy(value.as_bytes()).to_string();
        match name {
            b"White" => tags.white = Some(tag_value),
            b"Black" => tags.black = Some(tag_value),
            b"Site" => tags.site = Some(tag_value),
            b"FEN" => {
                let fen = match Fen::from_ascii(value.as_bytes()) {
                    Ok(fen) => fen,
                    Err(err) => return ControlFlow::Break(Err(format!("Invalid FEN tag: {err}"))),
                };
                let pos = match fen.into_position(CastlingMode::Standard) {
                    Ok(pos) => pos,
                    Err(err) => {
                        return ControlFlow::Break(Err(format!("Invalid FEN position: {err}")));
                    }
                };
                tags.fen = Some(pos);
            }
            _ => {}
        }
        ControlFlow::Continue(())
    }

    fn begin_movetext(&mut self, tags: Self::Tags) -> ControlFlow<Self::Output, Self::Movetext> {
        let white = tags.white.unwrap_or_default();
        let black = tags.black.unwrap_or_default();
        let user_lower = self.user.to_lowercase();
        let user_color = if user_lower == white.to_lowercase() {
            Some(Color::White)
        } else if user_lower == black.to_lowercase() {
            Some(Color::Black)
        } else {
            None
        };

        let position = tags.fen.unwrap_or_default();
        let ply = initial_ply(&position);
        let game_id = self
            .game_id_override
            .clone()
            .unwrap_or_else(|| tags.site.unwrap_or_default());

        ControlFlow::Continue(MovetextState {
            position,
            positions: Vec::new(),
            user_color,
            user: self.user.clone(),
            source: self.source.clone(),
            game_id,
            ply,
            last_position_index: None,
        })
    }

    fn san(
        &mut self,
        movetext: &mut Self::Movetext,
        san_plus: SanPlus,
    ) -> ControlFlow<Self::Output> {
        let mv = match san_plus.san.to_move(&movetext.position) {
            Ok(mv) => mv,
            Err(err) => return ControlFlow::Break(Err(format!("Invalid SAN move: {err}"))),
        };

        if let Some(color) = movetext.user_color {
            if movetext.position.turn() == color {
                let ply = movetext.ply;
                let move_number = ply / 2 + 1;
                let side_to_move = if movetext.position.turn() == Color::White {
                    "white"
                } else {
                    "black"
                };
                let fen = Fen::from_position(&movetext.position, EnPassantMode::Legal).to_string();
                let uci = UciMove::from_standard(mv).to_string();
                let san = san_plus.to_string();
                let record = PositionRecord {
                    game_id: movetext.game_id.clone(),
                    user: movetext.user.clone(),
                    source: movetext.source.clone(),
                    fen,
                    ply,
                    move_number,
                    side_to_move: side_to_move.to_string(),
                    uci,
                    san,
                    clock_seconds: None,
                };
                movetext.positions.push(record);
                movetext.last_position_index = Some(movetext.positions.len() - 1);
            } else {
                movetext.last_position_index = None;
            }
        }

        movetext.ply = movetext.ply.saturating_add(1);
        movetext.position = match movetext.position.clone().play(mv) {
            Ok(pos) => pos,
            Err(err) => return ControlFlow::Break(Err(format!("Illegal move in PGN: {err}"))),
        };
        ControlFlow::Continue(())
    }

    fn comment(
        &mut self,
        movetext: &mut Self::Movetext,
        comment: RawComment<'_>,
    ) -> ControlFlow<Self::Output> {
        if let Some(index) = movetext.last_position_index {
            if let Some(clock) = parse_clock(comment.as_bytes()) {
                if let Some(record) = movetext.positions.get_mut(index) {
                    record.clock_seconds = Some(clock);
                }
            }
            movetext.last_position_index = None;
        }
        ControlFlow::Continue(())
    }

    fn end_game(&mut self, movetext: Self::Movetext) -> Self::Output {
        Ok(movetext.positions)
    }
}

fn parse_clock(comment: &[u8]) -> Option<f64> {
    let text = String::from_utf8_lossy(comment);
    let marker = text.find("%clk")?;
    let after = text[marker + 4..].trim_start();
    let token: String = after
        .chars()
        .take_while(|ch| ch.is_ascii_digit() || *ch == ':' || *ch == '.')
        .collect();
    if token.is_empty() {
        return None;
    }
    let parts: Vec<&str> = token.split(':').collect();
    let (hours, minutes, seconds) = match parts.len() {
        3 => (parts[0], parts[1], parts[2]),
        2 => ("0", parts[0], parts[1]),
        _ => return None,
    };
    let hours = hours.parse::<f64>().ok()?;
    let minutes = minutes.parse::<f64>().ok()?;
    let seconds = seconds.parse::<f64>().ok()?;
    Some(hours * 3600.0 + minutes * 60.0 + seconds)
}

fn initial_ply(position: &Chess) -> u32 {
    let fullmoves = position.fullmoves().get();
    let base = (fullmoves - 1) * 2;
    let offset = if position.turn() == Color::Black {
        1
    } else {
        0
    };
    base + offset
}

#[pyfunction]
fn extract_positions(
    pgn: &str,
    user: &str,
    source: &str,
    game_id: Option<&str>,
) -> PyResult<Vec<PyObject>> {
    let mut reader = Reader::new(Cursor::new(pgn.as_bytes()));
    let mut visitor = ExtractVisitor::new(user, source, game_id);
    let parsed = match reader.read_game(&mut visitor) {
        Ok(output) => output,
        Err(err) => {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "PGN parse error: {err}"
            )));
        }
    };

    let records = match parsed {
        Some(Ok(records)) => records,
        Some(Err(err)) => {
            return Err(pyo3::exceptions::PyValueError::new_err(err));
        }
        None => Vec::new(),
    };

    Python::with_gil(|py| {
        let mut output = Vec::with_capacity(records.len());
        for record in records {
            let dict = PyDict::new(py);
            dict.set_item("game_id", record.game_id)?;
            dict.set_item("user", record.user)?;
            dict.set_item("source", record.source)?;
            dict.set_item("fen", record.fen)?;
            dict.set_item("ply", record.ply)?;
            dict.set_item("move_number", record.move_number)?;
            dict.set_item("side_to_move", record.side_to_move)?;
            dict.set_item("uci", record.uci)?;
            dict.set_item("san", record.san)?;
            dict.set_item("clock_seconds", record.clock_seconds)?;
            output.push(dict.into());
        }
        Ok(output)
    })
}

#[pyfunction]
fn hello_from_bin() -> String {
    "Hello from tactix!".to_string()
}

/// A Python module implemented in Rust. The name of this module must match
/// the `lib.name` setting in the `Cargo.toml`, else Python will not be able to
/// import the module.
#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(extract_positions, m)?)?;
    m.add_function(wrap_pyfunction!(hello_from_bin, m)?)?;
    Ok(())
}
