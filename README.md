# library-management-system
Sistema de gestión de una biblioteca.

Entities
- User
- Book
- Author
- Loan
- Hold
- Fine

Business Rules

- A user can have a maximum of 5 active loans.

- A book that is already checked out cannot be checked out again.

- A hold can only be placed if the book is unavailable.

- A late return incurs a fine.

- If there is a hold, the next loan must be for the first user in the queue.

- Users with outstanding fines cannot request new books.

- A book can be marked as lost.

- If a book is lost, it cannot be checked out again.

- Administrators can only delete books if they have no active loans.