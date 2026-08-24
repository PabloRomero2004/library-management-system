# BUSINESS_RULES

## 1. Purpose

This document defines the business rules and domain constraints for the **system-library-management** project.

These rules describe the expected behavior of the library management domain independently from implementation details, APIs, databases, frameworks, or user interface decisions. The system must enforce these rules consistently across all application layers.

The main domain entities are:

* User
* Book
* Author
* Loan
* Hold
* Fine

---

# 2. General Principles

## 2.1 Data Integrity

All operations must preserve the consistency of the library system.

An operation that violates a business rule must be rejected and must not leave the system in a partially updated or inconsistent state.

For example, if creating a loan requires updating both the book availability and the user's active loan count, both changes must succeed or neither change must be applied.

## 2.2 Entity Identity

Each entity must have a unique identifier.

A deleted or inactive entity identifier must not be reassigned to another entity.

## 2.3 Historical Records

Historical records such as completed loans, returned books, paid fines, and cancelled holds should not be physically deleted when they are required for auditing or reporting purposes.

Instead, the system should preserve the historical record and update its status when appropriate.

## 2.4 Validation

Business rules must not rely exclusively on client-side validation.

All critical rules must be enforced by the domain or application layer, even if the user interface also validates the same conditions.

---

# 3. User Rules

## 3.1 User Registration

A user must have a unique identifier.

A user must have all mandatory information required by the system before being allowed to perform library operations.

The system must reject the creation of duplicate users according to the uniqueness criteria defined by the application, such as a library card number or email address.

## 3.2 User Status

A user may have one of the following statuses:

* Active
* Suspended
* Inactive

Only active users may create new loans or place new holds.

Suspended or inactive users cannot check out books or create holds.

Existing historical loans and fines must remain associated with the user even if the user becomes inactive.

## 3.3 Maximum Active Loans

A user can have a maximum of **5 active loans** at the same time.

An active loan is a loan that has been created but has not yet been returned.

The system must reject a new loan if creating it would cause the user to exceed the maximum number of active loans.

## 3.4 Outstanding Fines

Users with outstanding fines cannot request new books or create new holds.

The system may allow a user with outstanding fines to return books.

A fine is considered outstanding until it has been fully paid, waived, or otherwise resolved according to the system rules.

## 3.5 User Deactivation

A user should not be permanently deleted if the user has historical loans, holds, or fines.

A user with active loans should not be deactivated unless the active loans are resolved or explicitly transferred to an administrative resolution process.

---

# 4. Book Rules

## 4.1 Book Availability

A book must have a status that represents its current availability.

Possible statuses may include:

* Available
* Checked Out
* Reserved
* Lost
* Unavailable

A book can only be checked out when its status allows borrowing.

## 4.2 Checked Out Books

A book that is already checked out cannot be checked out again.

The system must ensure that a book cannot have more than one active loan at the same time.

## 4.3 Lost Books

A book can be marked as lost.

Once a book is marked as lost:

* It cannot be checked out.
* It cannot be selected as available for a new loan.
* Existing holds for the book must not result in a new loan until the book becomes available again.
* The book must remain in the system for historical and auditing purposes.

If the system allows a lost book to be recovered, an administrator must explicitly change its status before the book can become available again.

## 4.4 Book Deletion

Administrators can only delete a book if it has no active loans.

A book with active holds should not be permanently deleted. The holds must first be cancelled or otherwise resolved.

If a book has historical loans, the preferred behavior is to archive or deactivate the book rather than physically delete it.

## 4.5 Book Availability After Return

When a book is returned:

* The active loan must be closed.
* The return date must be recorded.
* Any applicable fine must be calculated.
* The system must check whether active holds exist for the book.

If there are no active holds, the book may become available.

If active holds exist, the book must follow the hold fulfillment process.

---

# 5. Author Rules

## 5.1 Author Association

A book must be associated with at least one author unless the system explicitly supports anonymous or unknown authors.

An author may be associated with multiple books.

## 5.2 Author Deletion

An author should not be deleted if one or more books are associated with that author.

If author removal is required, the system should either:

* Remove the association only when allowed, or
* Mark the author as inactive or archived.

Deleting an author must not leave existing books with invalid references.

## 5.3 Duplicate Authors

The system should prevent accidental duplicate author records.

If two author records represent the same person, they should be merged or resolved according to administrative rules rather than creating inconsistent book associations.

---

# 6. Loan Rules

## 6.1 Loan Creation

A loan can only be created when all of the following conditions are satisfied:

* The user exists.
* The user is active.
* The user has fewer than 5 active loans.
* The user has no outstanding fines that block borrowing.
* The book exists.
* The book is available for checkout.
* The book is not marked as lost.
* The book is not already associated with another active loan.
* The hold queue rules are satisfied.

If any of these conditions fail, the loan must not be created.

## 6.2 Loan Dates

Every loan must have:

* A loan start date.
* A due date.
* A loan status.

A due date must be later than or equal to the loan start date according to the configured borrowing policy.

A returned loan must also have a return date.

## 6.3 Active Loan Uniqueness

A book can have only one active loan at a time.

A user cannot have multiple active loans for the same physical book.

## 6.4 Loan Renewal

A loan may only be renewed when all applicable renewal conditions are satisfied.

A loan cannot be renewed if:

* The loan has already been returned.
* The book has been marked as lost.
* A renewal would violate the maximum renewal limit.
* Another user has an active hold for the book.
* The user is no longer eligible to borrow.

The renewal operation must update the due date without creating a duplicate active loan.

## 6.5 Returning a Book

A book can only be returned if there is an active loan associated with it.

Returning a book must close the active loan exactly once.

Attempting to return the same loan multiple times must not create duplicate fines or duplicate state changes.

---

# 7. Hold Rules

## 7.1 Hold Eligibility

A hold can only be placed if the requested book is currently unavailable for immediate checkout.

A hold must not be created for a book that is available unless the system explicitly supports advance reservations.

A user must be eligible to borrow before creating a hold.

Therefore, a user cannot create a new hold if the user:

* Is inactive.
* Is suspended.
* Has outstanding fines that block borrowing.

## 7.2 Hold Queue

Holds for the same book must be processed using a first-in, first-out order.

The position in the queue must be determined by the hold creation time or another deterministic ordering mechanism.

If multiple holds are created at the same logical time, the system must use a stable secondary ordering mechanism.

## 7.3 Hold Fulfillment

If there is an active hold queue, the next loan must be offered to the first eligible user in the queue.

A book must not be loaned to a user who is behind another eligible user in the hold queue.

If the first user in the queue is no longer eligible, the hold must be skipped, cancelled, or marked as expired according to the hold policy before the next eligible user can receive the book.

## 7.4 Duplicate Holds

A user cannot have multiple active holds for the same book.

The system must reject duplicate active hold requests.

## 7.5 Hold Cancellation

A user may cancel an active hold before it has been fulfilled.

When a hold is cancelled, it must be removed from the active queue without affecting the order of the remaining holds.

A fulfilled or expired hold should not be treated as an active hold.

## 7.6 Hold Expiration

If the system supports hold expiration, an available book assigned to a user must only remain reserved for the configured pickup period.

After the reservation period expires:

* The hold must be marked as expired.
* The book must be offered to the next eligible user in the queue.
* If no eligible holds remain, the book may become available.

---

# 8. Fine Rules

## 8.1 Late Returns

A late return incurs a fine when the actual return date is later than the loan due date.

No late fine should be created when the book is returned on or before the due date.

## 8.2 Fine Calculation

The fine amount must be calculated using the configured fine policy.

The calculation may depend on:

* Number of overdue days.
* Fine amount per day.
* Maximum fine amount.
* Grace period, if applicable.

The same fine calculation rules must be applied consistently.

## 8.3 Fine Association

A fine must be associated with the relevant user and, when applicable, with the loan that caused the fine.

The system must preserve enough information to determine why the fine was created.

## 8.4 Fine Payment

A fine cannot be considered resolved until its outstanding amount reaches zero or the fine is explicitly waived.

A payment amount must not reduce the outstanding balance below zero unless the system explicitly supports credits or refunds.

## 8.5 Duplicate Fine Prevention

The same overdue event must not generate multiple duplicate fines.

Retrying a return operation or processing the same event more than once must not result in duplicated charges.

---

# 9. Book and Hold Interaction Rules

When a book is returned and one or more active holds exist, the book must not become generally available before the hold queue is processed.

The system must identify the first eligible user in the hold queue.

The book may then be marked as reserved or otherwise assigned to that user.

Users later in the queue must not bypass earlier eligible users.

If no eligible users remain in the hold queue, the book may become available.

---

# 10. Administrative Rules

## 10.1 Book Management

Administrators may create, update, archive, or delete books according to the integrity rules defined in this document.

Administrators cannot delete a book with an active loan.

Administrators should not delete a book with active holds without first resolving those holds.

## 10.2 Status Changes

Administrative actions that change the status of a book, user, loan, hold, or fine must preserve domain consistency.

For example, an administrator cannot mark a book as available while it has an active loan.

## 10.3 Lost Book Management

Only authorized administrative operations may mark a book as lost or restore a lost book.

Changing a book from `Lost` to `Available` must not automatically ignore existing active holds.

The hold queue must still be respected.

## 10.4 Administrative Overrides

If the system supports administrative overrides of normal business rules, those overrides should:

* Require appropriate authorization.
* Be explicitly recorded.
* Preserve an audit trail.
* Include the reason for the override.

Administrative overrides must not silently bypass critical integrity constraints.

---

# 11. State Consistency Rules

The following conditions must always be true:

* A checked-out book must have exactly one active loan.
* A book with an active loan cannot be available.
* A lost book cannot have a new active loan.
* A returned loan cannot remain active.
* A user cannot exceed the maximum number of active loans.
* A user cannot have more than one active hold for the same book.
* A book cannot be loaned to a user who improperly bypasses an eligible user earlier in the hold queue.
* A resolved fine must not be treated as an outstanding fine.
* A user blocked by outstanding fines cannot create new loans or holds.
* A deleted entity must not leave invalid references in related records.

---

# 12. Error Handling Requirements

When a business rule is violated, the system must return or raise a meaningful domain-level error.

Errors should identify the business reason for the failure without exposing unnecessary implementation details.

Examples include:

* `MAXIMUM_ACTIVE_LOANS_REACHED`
* `BOOK_NOT_AVAILABLE`
* `BOOK_ALREADY_CHECKED_OUT`
* `BOOK_IS_LOST`
* `USER_NOT_ELIGIBLE`
* `USER_HAS_OUTSTANDING_FINES`
* `ACTIVE_HOLD_ALREADY_EXISTS`
* `HOLD_QUEUE_PRIORITY_VIOLATION`
* `LOAN_NOT_ACTIVE`
* `BOOK_HAS_ACTIVE_LOAN`
* `BOOK_HAS_ACTIVE_HOLDS`
* `AUTHOR_HAS_ASSOCIATED_BOOKS`

The application should avoid using generic technical errors to represent expected business rule violations.

---

# 13. Concurrency and Consistency

Operations that can affect availability, loans, holds, or fines must be protected against inconsistent concurrent updates.

For example, if two users attempt to check out the same available book at the same time, the system must guarantee that only one active loan is created.

Similarly, concurrent hold requests must result in a deterministic queue order.

The system must enforce critical constraints at a level that prevents race conditions from violating business rules.

---

# 14. Retry and Idempotency Rules

Operations that may be retried due to technical failures must not create duplicate domain effects.

Examples include:

* Returning a book multiple times must not create multiple fines.
* Retrying a successful loan request must not create duplicate active loans.
* Retrying a fine payment must not record the same payment multiple times.
* Retrying hold cancellation must not corrupt the hold queue.

Where appropriate, commands should be idempotent or protected by a unique operation identifier.

---

# 15. Rule Priority

When multiple business rules apply to the same operation, the system should validate them in an order that avoids invalid state transitions.

For example, before creating a loan, the system should first verify that:

1. The user exists and is active.
2. The user is eligible to borrow.
3. The user has no blocking outstanding fines.
4. The user has not reached the maximum active loan limit.
5. The book exists.
6. The book is not lost.
7. The book is available.
8. No other active loan exists for the book.
9. The hold queue rules allow the user to borrow the book.

The operation must only be completed when all required rules are satisfied.

