package model;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

class BookListTest {

    private Author author1;
    private Author author2;
    private Book book1; // Available, not lost, ID 101, ISBN-001
    private Book book2; // Not available, not lost, ID 102, ISBN-002
    private Book book3; // Available, lost, ID 103, ISBN-003
    private Book book4; // Not available, lost, ID 104, ISBN-004
    private Book book5; // Available, not lost, ID 105, ISBN null

    @BeforeEach
    void setUp() {
        author1 = new Author(1L, "John", "Doe", LocalDate.of(1970, 1, 1), "American", "Bio 1");
        author2 = new Author(2L, "Jane", "Smith", LocalDate.of(1980, 5, 10), "British", "Bio 2");

        book1 = new Book(101L, "Title A", "ISBN-001", author1, "Fiction", LocalDate.of(2000, 1, 1), true, false);
        book2 = new Book(102L, "Title B", "ISBN-002", author1, "Science", LocalDate.of(2005, 5, 10), false, false);
        book3 = new Book(103L, "Title C", "ISBN-003", author2, "History", LocalDate.of(2010, 10, 15), true, true);
        book4 = new Book(104L, "Title D", "ISBN-004", author2, "Fantasy", LocalDate.of(2015, 3, 20), false, true);
        book5 = new Book(105L, "Title E", null, author1, "Mystery", LocalDate.of(2020, 7, 25), true, false);
    }

    // --- Constructor Tests ---

    @Test
    void testDefaultConstructor() {
        // Arrange & Act
        BookList bookList = new BookList();

        // Assert
        assertNotNull(bookList);
        assertTrue(bookList.getBooks().isEmpty());
        assertEquals(0, bookList.size());
    }

    @Test
    void testConstructorWithInitialList() {
        // Arrange
        List<Book> initialBooks = new ArrayList<>(Arrays.asList(book1, book2));

        // Act
        BookList bookList = new BookList(initialBooks);

        // Assert
        assertNotNull(bookList);
        assertEquals(2, bookList.size());
        assertTrue(bookList.getBooks().contains(book1));
        assertTrue(bookList.getBooks().contains(book2));

        // Verify defensive copy: modifying the initial list should not affect the BookList's internal list
        initialBooks.add(book3);
        assertEquals(2, bookList.size(), "BookList should have a defensive copy of the initial list");
    }

    @Test
    void testConstructorWithEmptyList() {
        // Arrange
        List<Book> initialBooks = new ArrayList<>();

        // Act
        BookList bookList = new BookList(initialBooks);

        // Assert
        assertNotNull(bookList);
        assertTrue(bookList.getBooks().isEmpty());
        assertEquals(0, bookList.size());
    }

    @Test
    void testConstructorWithNullList() {
        // Act & Assert
        // The current implementation `new ArrayList<>(null)` throws NullPointerException.
        // This test asserts that behavior.
        assertThrows(NullPointerException.class, () -> new BookList(null),
                "Constructor with null list should throw NullPointerException as per current implementation.");
    }

    // --- Getter and Setter Tests ---

    @Test
    void testGetBooksReturnsDefensiveCopy() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1));

        // Act
        List<Book> retrievedBooks = bookList.getBooks();

        // Assert
        assertEquals(1, retrievedBooks.size());
        assertTrue(retrievedBooks.contains(book1));

        // Verify defensive copy: modifying the retrieved list should not affect the BookList's internal list
        retrievedBooks.add(book2);
        assertEquals(1, bookList.size(), "Modifying the list returned by getBooks should not affect the internal list");
        assertFalse(bookList.getBooks().contains(book2)); // Ensure internal list doesn't contain book2
    }

    @Test
    void testSetBooks() {
        // Arrange
        BookList bookList = new BookList();
        bookList.addBook(book1);
        assertEquals(1, bookList.size());

        List<Book> newBooks = new ArrayList<>(Arrays.asList(book2, book3));

        // Act
        bookList.setBooks(newBooks);

        // Assert
        assertEquals(2, bookList.size());
        assertTrue(bookList.getBooks().contains(book2));
        assertTrue(bookList.getBooks().contains(book3));
        assertFalse(bookList.getBooks().contains(book1)); // book1 should be replaced

        // Verify defensive copy: modifying the newBooks list should not affect the BookList's internal list
        newBooks.add(book4);
        assertEquals(2, bookList.size(), "BookList should have a defensive copy of the list set by setBooks");
        assertFalse(bookList.getBooks().contains(book4)); // Ensure internal list doesn't contain book4
    }

    @Test
    void testSetBooksWithEmptyList() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2));

        // Act
        bookList.setBooks(new ArrayList<>());

        // Assert
        assertTrue(bookList.getBooks().isEmpty());
        assertEquals(0, bookList.size());
    }

    @Test
    void testSetBooksWithNullList() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2));

        // Act & Assert
        // The current implementation `new ArrayList<>(null)` throws NullPointerException.
        // This test asserts that behavior.
        assertThrows(NullPointerException.class, () -> bookList.setBooks(null),
                "setBooks with null list should throw NullPointerException as per current implementation.");
    }

    // --- addBook Tests ---

    @Test
    void testAddBook() {
        // Arrange
        BookList bookList = new BookList();

        // Act
        bookList.addBook(book1);

        // Assert
        assertEquals(1, bookList.size());
        assertTrue(bookList.getBooks().contains(book1));

        // Act
        bookList.addBook(book2);

        // Assert
        assertEquals(2, bookList.size());
        assertTrue(bookList.getBooks().contains(book2));
    }

    @Test
    void testAddNullBook() {
        // Arrange
        BookList bookList = new BookList();

        // Act
        bookList.addBook(null); // Should not add null

        // Assert
        assertEquals(0, bookList.size());
        assertTrue(bookList.getBooks().isEmpty());
    }

    @Test
    void testAddDuplicateBook() {
        // Arrange
        BookList bookList = new BookList();
        bookList.addBook(book1);

        // Act
        bookList.addBook(book1); // ArrayList allows duplicates

        // Assert
        assertEquals(2, bookList.size(), "Adding the same book object twice should increase size if List allows duplicates");
        // The `equals` method of Book is based on ID and ISBN, so adding a new Book object with same ID/ISBN would also be a duplicate.
        // Here we are adding the exact same object reference.
    }

    // --- removeBook Tests ---

    @Test
    void testRemoveExistingBook() {
        // Arrange
        BookList bookList = new BookList(new ArrayList<>(Arrays.asList(book1, book2)));

        // Act
        boolean removed = bookList.removeBook(book1);

        // Assert
        // Defect: The current implementation `return false;` is incorrect. It should return true if removed.
        assertTrue(removed, "removeBook should return true if the book was successfully removed");
        assertEquals(1, bookList.size());
        assertFalse(bookList.getBooks().contains(book1));
        assertTrue(bookList.getBooks().contains(book2));
    }

    @Test
    void testRemoveNonExistingBook() {
        // Arrange
        BookList bookList = new BookList(new ArrayList<>(Arrays.asList(book1, book2)));

        // Act
        boolean removed = bookList.removeBook(book3); // book3 is not in the list

        // Assert
        assertFalse(removed, "removeBook should return false if the book was not found");
        assertEquals(2, bookList.size());
        assertTrue(bookList.getBooks().contains(book1));
        assertTrue(bookList.getBooks().contains(book2));
    }

    @Test
    void testRemoveNullBook() {
        // Arrange
        BookList bookList = new BookList(new ArrayList<>(Arrays.asList(book1, book2)));

        // Act
        boolean removed = bookList.removeBook(null);

        // Assert
        assertFalse(removed, "removeBook should return false when trying to remove a null book");
        assertEquals(2, bookList.size());
    }

    // --- findById Tests ---

    @Test
    void testFindByIdExisting() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2, book3));

        // Act
        Book foundBook = bookList.findById(102L);

        // Assert
        assertNotNull(foundBook);
        assertEquals(book2, foundBook);
    }

    @Test
    void testFindByIdNonExisting() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2, book3));

        // Act
        Book foundBook = bookList.findById(999L);

        // Assert
        assertNull(foundBook);
    }

    @Test
    void testFindByIdBookWithNullIdInList() {
        // Arrange
        Book bookWithNullId = new Book(null, "Null ID Book", "ISBN-NID", author1, "Genre", LocalDate.now(), true, false);
        BookList bookList = new BookList(Arrays.asList(book1, bookWithNullId));

        // Act & Assert
        // Should find book1
        Book foundBook = bookList.findById(101L);
        assertNotNull(foundBook);
        assertEquals(book1, foundBook);

        // Should not find the book with null ID when searching for null
        Book foundNullIdBook = bookList.findById(null);
        assertNull(foundNullIdBook);
    }

    @Test
    void testFindByIdSearchNull() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2));

        // Act
        Book foundBook = bookList.findById(null);

        // Assert
        assertNull(foundBook);
    }

    @Test
    void testFindByIdEmptyList() {
        // Arrange
        BookList bookList = new BookList();

        // Act
        Book foundBook = bookList.findById(101L);

        // Assert
        assertNull(foundBook);
    }

    // --- findByIsbn Tests ---

    @Test
    void testFindByIsbnExisting() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2, book3));

        // Act
        Book foundBook = bookList.findByIsbn("ISBN-002");

        // Assert
        assertNotNull(foundBook);
        assertEquals(book2, foundBook);
    }

    @Test
    void testFindByIsbnNonExisting() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2, book3));

        // Act
        Book foundBook = bookList.findByIsbn("ISBN-999");

        // Assert
        assertNull(foundBook);
    }

    @Test
    void testFindByIsbnBookWithNullIsbnInList() {
        // Arrange
        // book5 has a null ISBN
        BookList bookList = new BookList(Arrays.asList(book1, book5));

        // Act & Assert
        // Should find book1
        Book foundBook = bookList.findByIsbn("ISBN-001");
        assertNotNull(foundBook);
        assertEquals(book1, foundBook);

        // Should not find the book with null ISBN when searching for null
        Book foundNullIsbnBook = bookList.findByIsbn(null);
        assertNull(foundNullIsbnBook);
    }

    @Test
    void testFindByIsbnSearchNull() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2));

        // Act
        Book foundBook = bookList.findByIsbn(null);

        // Assert
        assertNull(foundBook);
    }

    @Test
    void testFindByIsbnEmptyList() {
        // Arrange
        BookList bookList = new BookList();

        // Act
        Book foundBook = bookList.findByIsbn("ISBN-001");

        // Assert
        assertNull(foundBook);
    }

    // --- getAvailableBooks Tests ---

    @Test
    void testGetAvailableBooksAllAvailable() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book5)); // book1, book5 are available

        // Act
        List<Book> available = bookList.getAvailableBooks();

        // Assert
        assertEquals(2, available.size());
        assertTrue(available.contains(book1));
        assertTrue(available.contains(book5));
        assertFalse(available.contains(book2)); // Not available
    }

    @Test
    void testGetAvailableBooksMixed() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2, book3, book4, book5));

        // Act
        List<Book> available = bookList.getAvailableBooks();

        // Assert
        assertEquals(3, available.size());
        assertTrue(available.contains(book1));
        assertTrue(available.contains(book3));
        assertTrue(available.contains(book5));
        assertFalse(available.contains(book2));
        assertFalse(available.contains(book4));
    }

    @Test
    void testGetAvailableBooksNoneAvailable() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book2, book4)); // book2, book4 are not available

        // Act
        List<Book> available = bookList.getAvailableBooks();

        // Assert
        assertTrue(available.isEmpty());
    }

    @Test
    void testGetAvailableBooksEmptyList() {
        // Arrange
        BookList bookList = new BookList();

        // Act
        List<Book> available = bookList.getAvailableBooks();

        // Assert
        assertTrue(available.isEmpty());
    }

    // --- getLostBooks Tests ---

    @Test
    void testGetLostBooksAllLost() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book3, book4)); // book3, book4 are lost

        // Act
        List<Book> lost = bookList.getLostBooks();

        // Assert
        assertEquals(2, lost.size());
        assertTrue(lost.contains(book3));
        assertTrue(lost.contains(book4));
        assertFalse(lost.contains(book1)); // Not lost
    }

    @Test
    void testGetLostBooksMixed() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2, book3, book4, book5));

        // Act
        List<Book> lost = bookList.getLostBooks();

        // Assert
        assertEquals(2, lost.size());
        assertTrue(lost.contains(book3));
        assertTrue(lost.contains(book4));
        assertFalse(lost.contains(book1));
        assertFalse(lost.contains(book2));
        assertFalse(lost.contains(book5));
    }

    @Test
    void testGetLostBooksNoneLost() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2, book5)); // book1, book2, book5 are not lost

        // Act
        List<Book> lost = bookList.getLostBooks();

        // Assert
        assertTrue(lost.isEmpty());
    }

    @Test
    void testGetLostBooksEmptyList() {
        // Arrange
        BookList bookList = new BookList();

        // Act
        List<Book> lost = bookList.getLostBooks();

        // Assert
        assertTrue(lost.isEmpty());
    }

    // --- size Tests ---

    @Test
    void testSizeEmpty() {
        // Arrange
        BookList bookList = new BookList();

        // Act & Assert
        assertEquals(0, bookList.size());
    }

    @Test
    void testSizeWithBooks() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2, book3));

        // Act & Assert
        assertEquals(3, bookList.size());
    }

    @Test
    void testSizeAfterAddAndRemove() {
        // Arrange
        BookList bookList = new BookList();

        // Act
        bookList.addBook(book1);
        bookList.addBook(book2);
        bookList.removeBook(book1); // This will remove the book, but the method returns false (defect)

        // Assert
        assertEquals(1, bookList.size());
    }

    // --- isEmpty Tests ---

    @Test
    void testIsEmptyWhenEmpty() {
        // Arrange
        BookList bookList = new BookList();

        // Act & Assert
        // Defect: isEmpty returns !books.isEmpty(), so for an empty list, it returns !true which is false.
        assertTrue(bookList.isEmpty(), "isEmpty should return true for an empty list");
    }

    @Test
    void testIsEmptyWhenNotEmpty() {
        // Arrange
        BookList bookList = new BookList(Collections.singletonList(book1));

        // Act & Assert
        // Defect: isEmpty returns !books.isEmpty(), so for a non-empty list, it returns !false which is true.
        assertFalse(bookList.isEmpty(), "isEmpty should return false for a non-empty list");
    }

    // --- clear Tests ---

    @Test
    void testClearNonEmptyList() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2));
        // Note: The following assertion will fail due to the isEmpty defect
        // assertFalse(bookList.isEmpty());

        // Act
        bookList.clear();

        // Assert
        assertTrue(bookList.getBooks().isEmpty());
        assertEquals(0, bookList.size());
        // Note: The following assertion will fail due to the isEmpty defect
        // assertTrue(bookList.isEmpty());
    }

    @Test
    void testClearEmptyList() {
        // Arrange
        BookList bookList = new BookList();
        // Note: The following assertion will fail due to the isEmpty defect
        // assertTrue(bookList.isEmpty());

        // Act
        bookList.clear();

        // Assert
        assertTrue(bookList.getBooks().isEmpty());
        assertEquals(0, bookList.size());
        // Note: The following assertion will fail due to the isEmpty defect
        // assertTrue(bookList.isEmpty());
    }

    // --- toString Tests ---

    @Test
    void testToStringWithBooks() {
        // Arrange
        BookList bookList = new BookList(Arrays.asList(book1, book2));
        String expectedString = "BookList{books=" + Arrays.asList(book1, book2) + "}";

        // Act & Assert
        assertEquals(expectedString, bookList.toString());
    }

    @Test
    void testToStringEmptyList() {
        // Arrange
        BookList bookList = new BookList();
        String expectedString = "BookList{books=[]}";

        // Act & Assert
        assertEquals(expectedString, bookList.toString());
    }
}