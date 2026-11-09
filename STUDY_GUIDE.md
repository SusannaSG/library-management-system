# Study guide: Library Management System

Read this before any interview where the project comes up. The goal is that you can explain every part in your own words. Spend about two hours: read the files in the order below, run the project, and do the exercises.

## 1. The big picture (say this in 30 seconds)

"It's a Django web app for a library. Librarians log in to issue and return books. The rules, like the 14-day limit, the 3-book limit and the Rs. 5 daily fine, live in one file, `services.py`, so the web pages and the REST API both use the same logic. I wrote 35 tests for the rules, the API and the pages."

## 2. Read the code in this order

1. **`library/models.py`** (the database tables)
   - `Book`, `Member` and `Loan` become SQL tables. A `Loan` links one book to one member with a `ForeignKey`.
   - `returned_on` is empty (`null`) until the book comes back. That one column tells you if a loan is active.
   - `available_copies` is not stored. It is worked out as total copies minus unreturned loans, so it can never get out of sync.
2. **`library/services.py`** (the rules, the most important file)
   - `issue_book`: checks copies and the 3-book limit, then creates a `Loan`.
   - `return_book`: sets `returned_on` and calculates the fine.
   - `@transaction.atomic` means "all or nothing". If something fails halfway, the database changes are undone.
   - `select_for_update()` locks the row so two librarians can't issue the last copy at the same moment.
3. **`library/api.py` and `serializers.py`** (the REST API)
   - A serializer turns a model into JSON and checks incoming JSON.
   - A `ViewSet` gives list, create, update and delete endpoints in a few lines. The router in `urls.py` builds the URLs.
   - Loans are read-only through the normal endpoints. You can only change them through `issue/` and `return/`, so nobody can skip the rules.
4. **`library/views.py` and `templates/`** (the web pages)
   - `@login_required` redirects anonymous users to the login page.
   - Returning a book is a POST-only view (`@require_POST`), because an action that changes data should never be a plain link.
   - The `messages` framework shows the green and red notices after an action.
5. **`library/tests.py`** (how we know it works)
   - Each test creates its own small set of data and checks one behaviour.

## 3. Run it and try things

- Log in as `librarian`, issue a book to Asha, then try to issue a fourth book to her. What happens, and which line of code causes it?
- Open `/api/books/?search=python` in the browser. Then call `/api/members/` without logging in. Why the different results?
- In `/admin/`, change a loan's due date to last week, then open the dashboard. Where does the fine come from?

## 4. Exercises (do at least two)

1. Change the fine to Rs. 10 per day. Which one number changes? Which tests fail, and why?
2. Add a `phone` field to `Member`. Run `makemigrations` and `migrate`. What did each command do?
3. Add a rule that a member with an unpaid fine over Rs. 100 can't borrow. Write a test first.

## 5. Questions you may be asked, with short answers

**Why put the rules in `services.py` and not in the views?**
Both the web page and the API need the same rules. Writing them once avoids the two getting out of step, and it lets me test the rules without a web request.

**What does `@transaction.atomic` do?**
It wraps the function in a database transaction. Either every change is saved or none is, so the data is never half-updated.

**How do you stop two people issuing the last copy?**
`select_for_update()` locks the book row inside the transaction, so the second request waits and then sees there are no copies left. On SQLite, which this project uses locally, the lock is not enforced the same way, so I would use PostgreSQL in production.

**What is a serializer?**
It converts a model object to JSON for the API and validates incoming JSON before it reaches the database.

**What is the difference between authentication and permissions here?**
Authentication is who you are (session or basic login). Permissions are what you may do. Books are readable by anyone, but changes need a login. Members need a login even to read, because they hold personal details.

**What status code do you return when a rule is broken, and why?**
409 Conflict, because the request is valid but conflicts with the current state, for example no copies left.

**What would you improve?**
Pagination for long lists, reminder emails for overdue books, separate roles for librarian and admin, and a production database with deployment.

**Did you write this alone?**
Be honest. A good answer: "I built it with AI assistance and then studied it, ran it, and extended it. I can walk through any file." Then be ready to prove it by walking through `services.py`.

## 6. Do not claim

- Do not say it is deployed unless you deploy it.
- Do not say it handles payments, emails or high traffic. It does not.
