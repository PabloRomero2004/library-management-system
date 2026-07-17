package model;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.Objects;

import static org.junit.jupiter.api.Assertions.*;

class BookTest {

    private Book book;
    private Author author;
    private LocalDate publicationDate;

    @BeforeEach
    void setUp() {
        author = new Author(1L, "John", "Doe", LocalDate.of(1970, 1, 1), "American", "Biography of John Doe");
        publicationDate = LocalDate.of(2020, 1, 1);
        book = new Book(1L, "Test Title", "1234567890", author, "Fiction", publicationDate, true, false);
    }

    @Test
    void testNoArgsConstructor() {
        Book defaultBook = new Book();
        assertNull(defaultBook.getId());
        assertNull(defaultBook.getTitle());
        assertNull(defaultBook.getIsbn());
        assertNull(defaultBook.getAuthor());
        assertNull(defaultBook.getGenre());
        assertNull(defaultBook.getPublicationDate());
        assertFalse(defaultBook.isAvailable());
        assertFalse(defaultBook.isLost());
    }

    @Test
    void testAllArgsConstructor() {
        assertEquals(1L, book.getId());
        assertEquals("Test Title", book.getTitle());
        assertEquals("1234567890", book.getIsbn());
        assertEquals(author, book.getAuthor());
        assertEquals("Fiction", book.getGenre());
        assertEquals(publicationDate, book.getPublicationDate());
        assertTrue(book.isAvailable());
        assertFalse(book.isLost());
    }

    @Test
    void testGetAndSetId() {
        Long newId = 2L;
        book.setId(newId);
        assertEquals(newId, book.getId());
    }

    @Test
    void testGetAndSetTitle() {
        String newTitle = "New Title";
        book.setTitle(newTitle);
        assertEquals(newTitle, book.getTitle());
    }

    @Test
    void testGetAndSetIsbn() {
        String newIsbn = "0987654321";
        book.setIsbn(newIsbn);
        assertEquals(newIsbn, book.getIsbn());
    }

    @Test
    void testGetAndSetAuthor() {
        Author newAuthor = new Author(2L, "Jane", "Smith", LocalDate.of(1980, 5, 10), "British", "Biography of Jane Smith");
        book.setAuthor(newAuthor);
        assertEquals(newAuthor, book.getAuthor());
    }

    @Test
    void testGetAndSetGenre() {
        String newGenre = "Fantasy";
        book.setGenre(newGenre);
        assertEquals(newGenre, book.getGenre());
    }

    @Test
    void testGetAndSetPublicationDate() {
        LocalDate newDate = LocalDate.of(2021, 3, 15);
        book.setPublicationDate(newDate);
        assertEquals(newDate, book.getPublicationDate());
    }

    @Test
    void testIsAndSetAvailable() {
        book.setAvailable(false);
        assertFalse(book.isAvailable());
        book.setAvailable(true);
        assertTrue(book.isAvailable());
    }

    @Test
    void testIsAndSetLost() {
        book.setLost(true);
        assertTrue(book.isLost());
        book.setLost(false);
        assertFalse(book.isLost());
    }

    @Test
    void testEquals_sameObject() {
        assertTrue(book.equals(book));
    }

    @Test
    void testEquals_nullObject() {
        assertFalse(book.equals(null));
    }

    @Test
    void testEquals_differentClass() {
        assertFalse(book.equals("a string"));
    }

    @Test
    void testEquals_equalObjects() {
        Book anotherBook = new Book(1L, "Different Title", "1234567890", author, "Different Genre", LocalDate.of(2022,1,1), false, true);
        assertTrue(book.equals(anotherBook));
    }

    @Test
    void testEquals_differentId() {
        Book anotherBook = new Book(2L, "Test Title", "1234567890", author, "Fiction", publicationDate, true, false);
        assertFalse(book.equals(anotherBook));
    }

    @Test
    void testEquals_differentIsbn() {
        Book anotherBook = new Book(1L, "Test Title", "0000000000", author, "Fiction", publicationDate, true, false);
        assertFalse(book.equals(anotherBook));
    }

    @Test
    void testEquals_differentIdAndIsbn() {
        Book anotherBook = new Book(2L, "Different Title", "0000000000", author, "Different Genre", LocalDate.of(2022,1,1), false, true);
        assertFalse(book.equals(anotherBook));
    }

    @Test
    void testHashCode_consistencyWithEquals() {
        Book anotherBook = new Book(1L, "Different Title", "1234567890", author, "Different Genre", LocalDate.of(2022,1,1), false, true);
        assertTrue(book.equals(anotherBook) && book.hashCode() == anotherBook.hashCode());
    }

    @Test
    void testHashCode_differentObjects() {
        Book differentBook = new Book(2L, "Another Title", "0000000000", author, "Fantasy", LocalDate.of(2023,1,1), true, false);
        assertNotEquals(book.hashCode(), differentBook.hashCode());
    }

    @Test
    void testHashCode_sameIdDifferentIsbn() {
        Book differentIsbnBook = new Book(1L, "Test Title", "0000000000", author, "Fiction", publicationDate, true, false);
        assertNotEquals(book.hashCode(), differentIsbnBook.hashCode());
    }

    @Test
    void testHashCode_differentIdSameIsbn() {
        Book differentIdBook = new Book(2L, "Test Title", "1234567890", author, "Fiction", publicationDate, true, false);
        assertNotEquals(book.hashCode(), differentIdBook.hashCode());
    }
}