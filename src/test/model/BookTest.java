package model;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.*;

class BookTest {

    private Book book1;
    private Book book2;
    private Book book3;
    private Author author1;
    private Author author2;

    @BeforeEach
    void setUp() {
        author1 = new Author(1L, "John", "Doe", LocalDate.of(1970, 1, 1), "American", "Bio 1");
        author2 = new Author(2L, "Jane", "Smith", LocalDate.of(1980, 5, 10), "British", "Bio 2");

        book1 = new Book(1L, "The Great Book", "978-1234567890", author1, "Fiction", LocalDate.of(2000, 1, 1), true, false);
        book2 = new Book(1L, "The Great Book", "978-1234567890", author1, "Fiction", LocalDate.of(2000, 1, 1), true, false); // Same as book1
        book3 = new Book(2L, "Another Book", "978-0987654321", author2, "Science", LocalDate.of(2010, 5, 10), false, true);
    }

    @Test
    void testDefaultConstructor() {
        Book book = new Book();
        assertNull(book.getId());
        assertNull(book.getTitle());
        assertNull(book.getIsbn());
        assertNull(book.getAuthor());
        assertNull(book.getGenre());
        assertNull(book.getPublicationDate());
        assertFalse(book.isAvailable());
        assertFalse(book.isLost());
    }

    @Test
    void testParameterizedConstructor() {
        assertEquals(1L, book1.getId());
        assertEquals("The Great Book", book1.getTitle());
        assertEquals("978-1234567890", book1.getIsbn());
        assertEquals(author1, book1.getAuthor());
        assertEquals("Fiction", book1.getGenre());
        assertEquals(LocalDate.of(2000, 1, 1), book1.getPublicationDate());
        assertTrue(book1.isAvailable());
        assertFalse(book1.isLost());
    }

    @Test
    void testGettersAndSetters() {
        Book book = new Book();

        book.setId(3L);
        assertEquals(3L, book.getId());

        book.setTitle("New Title");
        assertEquals("New Title", book.getTitle());

        book.setIsbn("978-1112223334");
        assertEquals("978-1112223334", book.getIsbn());

        book.setAuthor(author2);
        assertEquals(author2, book.getAuthor());

        book.setGenre("Fantasy");
        assertEquals("Fantasy", book.getGenre());

        LocalDate newDate = LocalDate.of(2020, 10, 20);
        book.setPublicationDate(newDate);
        assertEquals(newDate, book.getPublicationDate());

        book.setAvailable(false);
        assertFalse(book.isAvailable());

        book.setLost(true);
        assertTrue(book.isLost());
    }

    @Test
    void testEquals_SameObject() {
        assertTrue(book1.equals(book1));
    }

    @Test
    void testEquals_EqualObjects() {
        assertTrue(book1.equals(book2));
        assertTrue(book2.equals(book1)); // Symmetry
    }

    @Test
    void testEquals_DifferentObjects() {
        assertFalse(book1.equals(book3));
        assertFalse(book3.equals(book1)); // Symmetry
    }

    @Test
    void testEquals_NullObject() {
        assertFalse(book1.equals(null));
    }

    @Test
    void testEquals_DifferentClass() {
        assertFalse(book1.equals("A String"));
        assertFalse(book1.equals(author1));
    }

    @Test
    void testEquals_DifferentId() {
        Book differentIdBook = new Book(99L, "The Great Book", "978-1234567890", author1, "Fiction", LocalDate.of(2000, 1, 1), true, false);
        assertFalse(book1.equals(differentIdBook));
    }

    @Test
    void testEquals_DifferentIsbn() {
        Book differentIsbnBook = new Book(1L, "The Great Book", "977-0000000000", author1, "Fiction", LocalDate.of(2000, 1, 1), true, false);
        assertFalse(book1.equals(differentIsbnBook));
    }

    @Test
    void testEquals_DifferentIdAndIsbn() {
        assertFalse(book1.equals(book3));
    }

    @Test
    void testHashCode_EqualObjects() {
        assertEquals(book1.hashCode(), book2.hashCode());
    }

    @Test
    void testHashCode_DifferentObjects() {
        assertNotEquals(book1.hashCode(), book3.hashCode());
    }

    @Test
    void testHashCode_Consistency() {
        int initialHashCode = book1.hashCode();
        assertEquals(initialHashCode, book1.hashCode());
        book1.setTitle("Changed Title"); // Changing title should not affect hash code based on current implementation
        assertEquals(initialHashCode, book1.hashCode());
    }

    @Test
    void testHashCode_NullIdAndIsbn() {
        Book bookWithNulls = new Book();
        bookWithNulls.setId(null);
        bookWithNulls.setIsbn(null);
        Book otherBookWithNulls = new Book();
        otherBookWithNulls.setId(null);
        otherBookWithNulls.setIsbn(null);
        assertEquals(bookWithNulls.hashCode(), otherBookWithNulls.hashCode());
        assertTrue(bookWithNulls.equals(otherBookWithNulls));
    }
}