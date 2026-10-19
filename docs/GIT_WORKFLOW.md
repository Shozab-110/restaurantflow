# Make a change and push it to GitHub

RestaurantFlow is already connected to `https://github.com/Shozab-110/restaurantflow.git` on branch `main`. Pushing needs internet; editing, committing, and local app use can work offline.

**Code changes** (Python, templates, styles, scripts, documentation) are committed and pushed. **Restaurant changes** made in the frontend (users, menu prices, tables, orders, payments) are already stored in PostgreSQL; they do not use Git push.

## Using the VS Code terminal

```powershell
cd D:\restaurantflow
git status
git diff
# Stage the files you intend to share. Example:
git add templates/operations/pos.html
# Or stage all intended changes after reviewing git status:
# git add .
git diff --cached
git commit -m "Describe what changed"
git push origin main
```

Replace the example path/message with your actual changes. `.env`, `.local`, database contents/dumps, uploads, and the virtual environment are ignored. Always review `git diff --cached` so new customer files or credentials outside those ignored locations are not accidentally published. Do not use `git add -f` to include ignored local files.

For a documentation/template change, check the affected page and `python scripts/check_docs.py`. For Python/business logic, use your virtual environment and the checks in [Testing](TESTING.md). CSS/library changes need `npm run build`; include the changed compiled assets. Model changes need `python manage.py makemigrations` and the migration file, plus migration testing.

## Using VS Code buttons

Open **Source Control** (`Ctrl+Shift+G`), inspect each changed file, click **+** to stage it, enter a useful message, and choose **Commit**, then **Push**. If **Sync Changes** also pulls, inspect/resolve any conflicts and rerun relevant checks before pushing. Never accept a force-push prompt just to bypass a conflict.

If you edit on GitHub or another computer, first run `git pull --ff-only` while your working tree is clean. If it reports diverged history, stop and review the changes; do not use `--force` or destructive reset commands. A normal push never intentionally replaces someone else's commits.

Git authentication uses your existing credential manager. Do not put passwords or tokens into Git commands or remote URLs. A rejected sign-in needs your GitHub account/token reauthentication, not your RestaurantFlow owner password.

## What happens after push

GitHub Actions runs the configured PostgreSQL, frontend, configuration, and Docker checks. Open the repository's **Actions** tab and inspect the latest result. A successful source push **does not automatically update a running VPS**. Deployment is a separate step involving a backup, new source/image, migrations, static assets, and service restart; see [Deployment](DEPLOYMENT.md).

For larger changes, create a branch (`git switch -c feature/your-change`), push it (`git push -u origin feature/your-change`), and open a pull request. Keep live data and secrets out of branches as well as `main`.
