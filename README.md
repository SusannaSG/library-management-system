# Library Management System

A Python full-stack web application for running a small library: a Django + Django REST Framework backend, a SQL database and a Bootstrap 5 interface.

## Features

- **Books and members** with search by title, author, category or ISBN
- **Issue and return books** with library rules enforced in one place (`library/services.py`):
  - 14-day loan period
  - maximum of 3 books per member
  - a book cannot be issued when no copies are left
  - late returns are fined Rs. 5 per day
- **Dashboard** with totals, overdue books and fines collected
- **REST API** for books, members, loans and statistics
- **Role-based access**: anyone can read books through the API; everything else needs a login
- **Django admin** for managing all records
- **35 automated tests** covering fines, loan rules, the API and the web pages

## Run locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_library   # demo data and login: librarian / library12345
python manage.py runserver
```

Open http://127.0.0.1:8000/ and log in. The admin is at http://127.0.0.1:8000/admin/.

Run the tests with `python manage.py test`.

## REST API

| Method | Endpoint | Login needed | Purpose |
|---|---|---|---|
| GET | `/api/books/?search=python` | No | List or search books |
| POST / PUT / DELETE | `/api/books/`, `/api/books/<id>/` | Yes | Add, edit or remove books |
| GET, POST, PUT, DELETE | `/api/members/` | Yes | Manage members (details are private) |
| GET | `/api/loans/?status=active\|overdue\|returned` | Yes | List loans, optionally filtered |
| POST | `/api/loans/issue/` | Yes | Issue a book: `{"book": 1, "member": 2}` |
| POST | `/api/loans/<id>/return/` | Yes | Return a book and calculate any fine |
| GET | `/api/stats/` | Yes | Dashboard numbers |

Example:

```bash
curl -u librarian:library12345 -X POST -H "Content-Type: application/json" \
     -d '{"book": 1, "member": 1}' http://127.0.0.1:8000/api/loans/issue/
```

A broken rule returns HTTP 409 with a message, for example `{"error": "No copies of \"Night Train\" are available right now."}`.

## Project layout

- `library/models.py`: Book, Member and Loan tables, plus the library rule settings
- `library/services.py`: issue, return and fine logic
- `library/api.py` and `serializers.py`: the REST API
- `library/views.py`, `forms.py` and `templates/`: the web pages
- `library/tests.py`: the test suite

## Limits

This is a learning project. It uses SQLite and development settings, so it needs `DEBUG` turned off, a real `SECRET_KEY` and a production database before it is deployed. It has a single staff role and does not send reminder emails.
