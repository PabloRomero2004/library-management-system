# Standard Unit Testing with JUnit 5 (Java)

This guide provides a reference for writing clean, standard unit tests in pure Java using **JUnit 5 (JUnit Jupiter)** without external mocking frameworks or complex setup.

## 1. Required Dependencies

If using Maven or Gradle, include the standard **JUnit Jupiter API** and **Engine** dependencies:

### Maven (`pom.xml`)

```xml
<dependency>
    <groupId>org.junit.jupiter</groupId>
    <artifactId>junit-jupiter</artifactId>
    <version>5.10.2</version>
    <scope>test</scope>
</dependency>
```

### Gradle (`build.gradle`)

```groovy
testImplementation 'org.junit.jupiter:junit-jupiter:5.10.2'
test {
    useJUnitPlatform()
}
```

## 2. Anatomy of a Test Class

A standard JUnit 5 test class contains test methods annotated with `@Test`.

```java
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class BookCopyTest {

    @Test
    void testInitialStatusIsAvailable() {
        // 1. Arrange
        BookCopy copy = new BookCopy("ISBN-1234");

        // 2. Act
        BookCopyStatus status = copy.getStatus();

        // 3. Assert
        assertEquals(BookCopyStatus.AVAILABLE, status, "New copies should be available by default");
    }
}
```

## 3. Essential Lifecycle Annotations

Use lifecycle annotations to set up preconditions or tear down state before/after tests run.

| Annotation | Description |
| :--- | :--- |
| `@BeforeEach` | Runs **before every** `@Test` method in the class. Ideal for initializing fresh objects. |
| `@AfterEach` | Runs **after every** `@Test` method. Ideal for cleanup. |
| `@BeforeAll` | Runs **once before all** test methods (must be `static`). |
| `@AfterAll` | Runs **once after all** test methods (must be `static`). |

### Lifecycle Example

```java
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class LoanTest {

    private User user;
    private BookCopy bookCopy;

    @BeforeEach
    void setUp() {
        // Runs before EACH test to ensure test isolation
        user = new User("U001", "John Doe");
        bookCopy = new BookCopy("BC-001");
    }

    @Test
    void testCreateValidLoan() {
        Loan loan = new Loan(user, bookCopy, 14); // 14-day loan

        assertNotNull(loan);
        assertEquals(user, loan.getUser());
        assertEquals(bookCopy, loan.getBookCopy());
        assertEquals(14, loan.getDurationInDays());
    }
}
```

## 4. Standard Assertions Reference

Import assertions statically for cleaner code:

```java
import static org.junit.jupiter.api.Assertions.*;
```

| Assertion | Description |
| :--- | :--- |
| `assertEquals(expected, actual)` | Asserts that expected and actual values are equal. |
| `assertNotEquals(unexpected, actual)` | Asserts that values are not equal. |
| `assertTrue(booleanCondition)` | Asserts that a condition evaluates to `true`. |
| `assertFalse(booleanCondition)` | Asserts that a condition evaluates to `false`. |
| `assertNull(object)` | Asserts that an object reference is `null`. |
| `assertNotNull(object)` | Asserts that an object reference is **not** `null`. |
| `assertSame(expected, actual)` | Asserts that both references point to the **exact same object instance**. |
| `assertThrows(ExpectedException.class, () -> executable)` | Asserts that invoking the code throws the expected exception type. |

## 5. Testing Exceptions

To test business rule violations (e.g., trying to set a loan duration exceeding 30 days):

```java
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class LoanRulesTest {

    @Test
    void testLoanDurationExceedingOneMonthThrowsException() {
        User user = new User("U001", "Alice");
        BookCopy copy = new BookCopy("BC-100");

        // Asserts that an IllegalArgumentException is thrown when duration > 30 days
        IllegalArgumentException exception = assertThrows(
            IllegalArgumentException.class,
            () -> new Loan(user, copy, 35)
        );

        // Optionally check exception message
        assertTrue(exception.getMessage().contains("Duration cannot exceed 30 days"));
    }
}
```

## 6. Testing Collections and Lists

When testing relationships (e.g., verifying a `User` has multiple `Loan` or `Fine` objects):

```java
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class UserLoansTest {

    @Test
    void testAddLoanToUser() {
        User user = new User("U002", "Bob");
        BookCopy copy = new BookCopy("BC-200");
        Loan loan = new Loan(user, copy, 7);

        user.addLoan(loan);

        assertEquals(1, user.getLoans().size());
        assertTrue(user.getLoans().contains(loan));
    }
}
```

## 7. Best Practices for Standard Unit Testing

1. **Follow the AAA Pattern (Arrange, Act, Assert)**:
   * **Arrange**: Set up test objects and preconditions.
   * **Act**: Execute the method being tested.
   * **Assert**: Verify the actual output matches expected results.

2. **Test One Concept Per Method**: Keep tests short, focused, and readable.

3. **Ensure Test Independence**: Never rely on test methods running in a specific order. Use `@BeforeEach` to reset state.

4. **Descriptive Test Names**: Name methods clearly to reflect what is being tested (e.g., `testRenewLoanFailsWhenBookIsReserved()` instead of `testRenew()`).

5. **Test Edge Cases and Boundaries**: Do not rely exclusively on the "happy path". Test boundary conditions such as `null` arguments, empty lists, upper/lower limit thresholds (e.g., requesting a loan for 0 days vs. 30 vs. 31 days).

6. **Avoid Logic inside Test Code**: Keep tests linear and declarative. Do not include control flow constructs like `if/else` statements or `for/while` loops inside test methods, as they introduce bugs within tests themselves.

7. **Ensure Single-Reason Failures**: A test method should fail for exactly one clear reason. If a business rule fails, the test name and assertion message should immediately indicate which specific constraint was violated.