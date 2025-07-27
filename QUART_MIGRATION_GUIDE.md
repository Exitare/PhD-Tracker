# Flask to Quart Migration Guide

## Overview
This guide outlines the migration from Flask to Quart for the PhD-Tracker application. Quart is an async Python web microframework with the same API as Flask but with async/await support.

## Key Changes Made

### 1. Dependencies Updated
- `flask` → `quart`
- `flask-wtf` → `quart-wtf`
- `flask-login` → `quart-auth`
- `Flask-Mail` → `quart-mail`
- `waitress` → `hypercorn` (ASGI server)
- `dotenv` → `python-dotenv`

### 2. Core Application Changes

#### `src/__init__.py`
- Changed `Flask` import to `Quart`
- Replaced `LoginManager` with `AuthManager` from `quart-auth`
- Updated function signature: `def create_app() -> Quart:`
- Updated logging messages from `[Flask]` to `[Quart]`

#### `run.py`
- Added `asyncio` import
- Replaced Waitress with Hypercorn for production serving
- Updated logging messages from `[Flask]` to `[Quart]`

#### `src/extensions.py`
- Updated imports to use Quart equivalents
- `flask_mail` → `quart_mail`
- `flask_wtf` → `quart_wtf`

### 3. Forms Migration
- Updated all form classes to inherit from `QuartForm` instead of `FlaskForm`
- Files modified:
  - `src/forms/account_forms.py`
  - `src/forms/contact_form.py`

### 4. Route Pattern Changes

#### Authentication Changes
- `flask_login` functions → `quart_auth` equivalents:
  - `login_user()` → `login_user()`
  - `logout_user()` → `logout_user()`
  - `login_required` → `login_required`
  - `current_user` → `current_user`

#### Async Route Patterns
Routes now need to be async and use `await` for:
- `render_template()` → `await render_template()`
- `request.form` → `await request.form`
- `request.args` → `await request.args`
- `request.method` → `await request.method`
- `flash()` → `await flash()`

Example migration:
```python
# Flask
@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", projects=projects)

# Quart
@bp.route("/dashboard")
@login_required
async def dashboard():
    return await render_template("dashboard.html", projects=projects)
```

## Files That Still Need Migration

### Route Files (All need async/await updates)
- `src/routes/about.py`
- `src/routes/academia.py`
- `src/routes/account.py`
- `src/routes/admin.py`
- `src/routes/auth.py` (partially done)
- `src/routes/dashboard.py` (done)
- `src/routes/home.py`
- `src/routes/journal.py`
- `src/routes/milestone.py`
- `src/routes/notes.py`
- `src/routes/plans.py`
- `src/routes/project.py`
- `src/routes/revision.py`
- `src/routes/showcase.py`
- `src/routes/sub_project.py`
- `src/routes/venue.py`
- `src/routes/webhooks.py`

### Services (May need async updates)
- `src/services/mail_service.py`
- Any service that uses request context

## Installation and Setup

1. Install new dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python run.py --dev  # Development
python run.py        # Production with Hypercorn
```

## Key Differences to Remember

### Request Handling
```python
# Flask
data = request.form.get('field')
args = request.args.get('param')

# Quart
form = await request.form
data = form.get('field')
args = await request.args
param = args.get('param')
```

### Template Rendering
```python
# Flask
return render_template('template.html', data=data)

# Quart
return await render_template('template.html', data=data)
```

### Flash Messages
```python
# Flask
flash('Message', 'category')

# Quart
await flash('Message', 'category')
```

## Authentication Migration Notes

Quart-Auth works differently from Flask-Login:
- No `user_loader` decorator needed
- User loading is handled differently in routes
- Session management is built-in but may need adjustment

## Testing

After migration, test all routes to ensure:
1. Forms still work correctly
2. Authentication flows work
3. Database operations are unaffected
4. Templates render properly
5. Static files are served correctly

## Next Steps

1. Update all remaining route files with async/await patterns
2. Test the application thoroughly
3. Update any custom middleware or decorators
4. Consider performance improvements that async/await enables
5. Update documentation and deployment configurations

## Performance Benefits

With Quart, you can now:
- Handle concurrent requests more efficiently
- Use async database operations (if using async SQLAlchemy)
- Implement async background tasks
- Better handle I/O-bound operations
