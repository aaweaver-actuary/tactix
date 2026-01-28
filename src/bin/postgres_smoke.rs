use std::env;
use std::time::{SystemTime, UNIX_EPOCH};

use tokio_postgres::{Client, NoTls};

fn env_or_empty(key: &str) -> Option<String> {
    env::var(key).ok().filter(|value| !value.trim().is_empty())
}

fn build_connection_string() -> Option<String> {
    if let Some(dsn) = env_or_empty("TACTIX_POSTGRES_DSN") {
        return Some(dsn);
    }
    if let Some(dsn) = env_or_empty("TACTIX_POSTGRES_URL") {
        return Some(dsn);
    }
    if let Some(dsn) = env_or_empty("POSTGRES_URL") {
        return Some(dsn);
    }
    if let Some(dsn) = env_or_empty("DATABASE_URL") {
        return Some(dsn);
    }

    let host = env_or_empty("TACTIX_POSTGRES_HOST")?;
    let db = env_or_empty("TACTIX_POSTGRES_DB")?;
    let user = env_or_empty("TACTIX_POSTGRES_USER");
    let password = env_or_empty("TACTIX_POSTGRES_PASSWORD");
    let port = env_or_empty("TACTIX_POSTGRES_PORT").unwrap_or_else(|| "5432".to_string());
    let sslmode = env_or_empty("TACTIX_POSTGRES_SSLMODE").unwrap_or_else(|| "disable".to_string());

    let mut conn = format!("host={host} port={port} dbname={db} sslmode={sslmode}");
    if let Some(user) = user {
        conn.push_str(&format!(" user={user}"));
    }
    if let Some(password) = password {
        conn.push_str(&format!(" password={password}"));
    }
    Some(conn)
}

fn build_table_name() -> String {
    let run_id = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_millis())
        .unwrap_or(0);
    format!("rust_smoke_{run_id}")
}

async fn connect() -> Result<Client, Box<dyn std::error::Error>> {
    let conn_str = build_connection_string()
        .ok_or_else(|| "Missing Postgres connection info".to_string())?;
    let (client, connection) = tokio_postgres::connect(&conn_str, NoTls).await?;
    tokio::spawn(async move {
        if let Err(err) = connection.await {
            eprintln!("Postgres connection error: {err}");
        }
    });
    Ok(client)
}

async fn run_crud(client: &Client) -> Result<(), Box<dyn std::error::Error>> {
    let table = build_table_name();
    let create_stmt = format!(
        "CREATE TEMP TABLE {table} (id SERIAL PRIMARY KEY, name TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT now())"
    );
    client.batch_execute(&create_stmt).await?;

    let insert_stmt = format!("INSERT INTO {table} (name) VALUES ($1) RETURNING id");
    let name = format!("rust-{table}");
    let row = client.query_one(&insert_stmt, &[&name]).await?;
    let id: i32 = row.get(0);

    let count_stmt = format!("SELECT COUNT(*) FROM {table}");
    let count_row = client.query_one(&count_stmt, &[]).await?;
    let count: i64 = count_row.get(0);

    let update_stmt = format!("UPDATE {table} SET name = $1 WHERE id = $2");
    let updated_name = format!("rust-{table}-updated");
    client.execute(&update_stmt, &[&updated_name, &id]).await?;

    let select_stmt = format!("SELECT name FROM {table} WHERE id = $1");
    let selected_row = client.query_one(&select_stmt, &[&id]).await?;
    let selected_name: String = selected_row.get(0);

    let delete_stmt = format!("DELETE FROM {table} WHERE id = $1");
    client.execute(&delete_stmt, &[&id]).await?;

    let remaining_row = client.query_one(&count_stmt, &[]).await?;
    let remaining: i64 = remaining_row.get(0);

    let drop_stmt = format!("DROP TABLE {table}");
    client.batch_execute(&drop_stmt).await?;

    println!(
        "Rust CRUD ok: inserted={count}, selected='{selected_name}', remaining={remaining}"
    );
    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = connect().await?;
    if let Err(err) = run_crud(&client).await {
        eprintln!("Rust Postgres smoke test failed: {err}");
        return Err(err);
    }
    Ok(())
}
