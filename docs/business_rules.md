# Library Management System - Business Rules

This document defines the core domain concepts, entity relationships, operational business rules, and status lifecycles governing the Library Management System.

## 1. Domain Entities & Value Objects

### Main Entities

* **User**: Represents a library member who can request loans, create reservations, and incur fines.

* **BookCopy**: Represents a specific physical copy of a book available in the library inventory.

* **Loan**: Represents an active or historical borrowing transaction of a specific `BookCopy` by a `User`.

* **Reservation**: Represents a hold placed by a `User` on a specific `BookCopy` to be borrowed at a later time.

* **Fine**: Represents a penalty or restriction applied to a `User` due to overdue items, damage, or loss.

### Enums & Statuses

* **BookCopyStatus**: Defines the lifecycle state of a `BookCopy`:
  * `AVAILABLE`: The copy is on the shelf and eligible for immediate borrowing or reservation.
  * `LOANED`: The copy is currently borrowed by a user under an active `Loan`.
  * `RESERVED`: The copy is held for a specific user under an active `Reservation`.
  * `MAINTENANCE`: The copy is undergoing repair, binding, or administrative processing and cannot be borrowed or reserved.
  * `LOST`: The copy has been reported lost or damaged beyond use.

### Informational / Attribute Entities

* **Book**: Metadata entity attached to a `BookCopy` (contains details like Title, ISBN, Genre, etc.).

* **Author**: Informational entity attached to a `Book` representing the creator(s).

---

## 2. Entity Relationship Rules

### 2.1 Loan Relationships

* **User to Loan**: One-to-Many ($1 : N$). A `User` can have multiple `Loan` records over time, but a `Loan` must belong to exactly one `User`.

* **BookCopy to Loan**: One-to-One ($1 : 1$) for active loans. A `Loan` instance must be associated with exactly one `BookCopy`, and an active `Loan` can only belong to one single `BookCopy` at a time.

### 2.2 Reservation Relationships

* **User to Reservation**: One-to-Many ($1 : N$). A `User` can place multiple `Reservation` requests, but each `Reservation` belongs to exactly one `User`.

* **BookCopy to Reservation**: One-to-One ($1 : 1$) for active holds. A `Reservation` must reference a single `BookCopy`, and a reserved `BookCopy` can only have one active `Reservation` belonging to a single user.

### 2.3 Fine Relationships

* **User to Fine**: One-to-Many ($1 : N$). A `User` can incur multiple `Fine` instances, but each `Fine` record is uniquely associated with one `User`.

---

## 3. Core Business Rules

### BR-01: Book Copy Status Eligibility

* A `BookCopy` can **only** be reserved or borrowed if its `BookCopyStatus` is currently set to `AVAILABLE`.
* Items marked as `LOANED`, `RESERVED`, `MAINTENANCE`, or `LOST` are strictly unavailable for new loan or reservation requests.

### BR-02: Item Reservation Exclusivity & Fulfilling Holds

* A `User` **cannot** request or initiate a `Loan` for any `BookCopy` that currently has an active `Reservation` belonging to another user.
* **Reservation Fulfillment Exemption**: If a `User` holds the active `Reservation` on a `BookCopy`, that user is allowed to check out the item. Upon checkout:
  1. The existing `Reservation` is marked as fulfilled/consumed.
  2. A new `Loan` instance is created.
  3. The `BookCopyStatus` transitions from `RESERVED` to `LOANED`.

### BR-03: System Quantity Limits per User

* **Maximum Active Loans**: A single `User` cannot have more than **5 active loans** simultaneously.
* **Maximum Active Reservations**: A single `User` cannot have more than **3 active reservations** simultaneously.

### BR-04: Loan Duration, Extensions, and Early Returns

* **Initial Maximum Duration**: Every `Loan` must specify a duration requested by the `User`, not to exceed **1 month (30 days)**.
* **Loan Renewals**:
  * A `User` may extend/renew an active `Loan` **once** for an additional duration of up to **14 days**.
  * Renewals are **prohibited** if:
    1. The `BookCopy` has a pending `Reservation` by another user.
    2. The `User` currently has active penalties or unpaid fines.
    3. The initial loan is already overdue.
* **Early Return Handling**: When a `BookCopy` is returned prior to its due date:
  * The `Loan` status is closed.
  * If no other active `Reservation` exists for the item, the `BookCopyStatus` reverts immediately to `AVAILABLE`.
  * If a pending reservation exists, the `BookCopyStatus` transitions to `RESERVED` for the next user in line.

### BR-05: Pickup Expiration for Reserved Items

* When a `BookCopy` transitions to `RESERVED` for a user, the user is granted a pickup window of **5 calendar days**.
* If the user fails to check out the copy within the 5-day window, the `Reservation` automatically expires, and the copy reverts to `AVAILABLE`.

### BR-06: Overdue Penalties and Account Suspensions

* **Fine Generation**: A `Loan` is considered overdue if the `BookCopy` is not returned on or before the due date. An overdue status automatically generates a `Fine` record for the user.
* **Suspension Calculation**: For **every single calendar day** that passes past the due date without returning the `BookCopy`, the `User` receives **1 month of system account suspension**.
* **Suspension Restrictions**: During a suspension period, the user is strictly blocked from creating new `Loan` or `Reservation` requests.

### BR-07: Loss or Damage Penalties

* If a `BookCopy` is reported lost or permanently damaged by a `User`:
  1. The `BookCopyStatus` is set to `LOST`.
  2. A special `Fine` is issued equivalent to the replacement cost of the book plus an administrative fee.
  3. The `User` account is immediately suspended from making new loans or reservations until the fine is fully settled.