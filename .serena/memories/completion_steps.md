# Completion checklist

- Verify changes via UI with Puppeteer (no eval shortcuts); capture screenshots in verification/.
- Run targeted tests relevant to changes and ensure no regressions.
- Update feature_list.json ONLY by flipping the specific feature's "passes" field after verification.
- Update claude-progress.txt with summary, tests run, and screenshots.
- Keep frontend dev server running on port 5173 if started; avoid leaving extra background processes.
