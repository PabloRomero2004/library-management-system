package model;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.*;

class AuthorTest {

    private Author author;
    private LocalDate sampleBirthDate;

    @BeforeEach
    void setUp() {
        sampleBirthDate = LocalDate.of(1980, 1, 1);
        author = new Author(1L, "John", "Doe", sampleBirthDate, "American", "A prolific writer.");
    }

    @Test
    void testDefaultConstructor() {
        Author defaultAuthor = new Author();
        assertNull(defaultAuthor.getId());
        assertNull(defaultAuthor.getFirstName());
        assertNull(defaultAuthor.getLastName());
        assertNull(defaultAuthor.getBirthDate());
        assertNull(defaultAuthor.getNationality());
        assertNull(defaultAuthor.getBiography());
    }

    @Test
    void testAllArgsConstructor() {
        assertEquals(1L, author.getId());
        assertEquals("John", author.getFirstName());
        assertEquals("Doe", author.getLastName());
        assertEquals(sampleBirthDate, author.getBirthDate());
        assertEquals("American", author.getNationality());
        assertEquals("A prolific writer.", author.getBiography());
    }

    @Test
    void testGetAndSetId() {
        author.setId(2L);
        assertEquals(2L, author.getId());
    }

    @Test
    void testGetAndSetFirstName() {
        author.setFirstName("Jane");
        assertEquals("Jane", author.getFirstName());
    }

    @Test
    void testGetAndSetLastName() {
        author.setLastName("Smith");
        assertEquals("Smith", author.getLastName());
    }

    @Test
    void testGetAndSetBirthDate() {
        LocalDate newBirthDate = LocalDate.of(1990, 5, 15);
        author.setBirthDate(newBirthDate);
        assertEquals(newBirthDate, author.getBirthDate());
    }

    @Test
    void testGetAndSetNationality() {
        author.setNationality("British");
        assertEquals("British", author.getNationality());
    }

    @Test
    void testGetAndSetBiography() {
        author.setBiography("A new biography.");
        assertEquals("A new biography.", author.getBiography());
    }

    @Test
    void testGetFullName() {
        assertEquals("John Doe", author.getFullName());

        author.setFirstName("Jane");
        author.setLastName("Austen");
        assertEquals("Jane Austen", author.getFullName());

        author.setFirstName("SingleName");
        author.setLastName(null);
        assertEquals("SingleName", author.getFullName());

        author.setFirstName(null);
        author.setLastName("LastNameOnly");
        assertEquals("LastNameOnly", author.getFullName());

        author.setFirstName(null);
        author.setLastName(null);
        assertEquals("", author.getFullName());

        author.setFirstName("");
        author.setLastName("");
        assertEquals("", author.getFullName());
    }

    @Test
    void testEquals_SameObject() {
        assertTrue(author.equals(author));
    }

    @Test
    void testEquals_NullObject() {
        assertFalse(author.equals(null));
    }

    @Test
    void testEquals_DifferentClass() {
        assertFalse(author.equals("a string"));
    }

    @Test
    void testEquals_EqualObjects() {
        Author anotherAuthor = new Author(1L, "John", "Doe", LocalDate.of(1985, 2, 2), "Canadian", "Another bio.");
        assertTrue(author.equals(anotherAuthor));
    }

    @Test
    void testEquals_DifferentId() {
        Author anotherAuthor = new Author(2L, "John", "Doe", sampleBirthDate, "American", "A prolific writer.");
        assertFalse(author.equals(anotherAuthor));
    }

    @Test
    void testEquals_DifferentFirstName() {
        Author anotherAuthor = new Author(1L, "Jane", "Doe", sampleBirthDate, "American", "A prolific writer.");
        assertFalse(author.equals(anotherAuthor));
    }

    @Test
    void testEquals_DifferentLastName() {
        Author anotherAuthor = new Author(1L, "John", "Smith", sampleBirthDate, "American", "A prolific writer.");
        assertFalse(author.equals(anotherAuthor));
    }

    @Test
    void testEquals_NullFields() {
        Author author1 = new Author(null, null, null, null, null, null);
        Author author2 = new Author(null, null, null, LocalDate.now(), "French", "Some bio");
        assertTrue(author1.equals(author2)); // Only id, firstName, lastName are considered
    }

    @Test
    void testHashCode_EqualObjectsHaveSameHashCode() {
        Author anotherAuthor = new Author(1L, "John", "Doe", LocalDate.of(1985, 2, 2), "Canadian", "Another bio.");
        assertEquals(author.hashCode(), anotherAuthor.hashCode());
    }

    @Test
    void testHashCode_DifferentObjectsHaveDifferentHashCode() {
        Author differentAuthor = new Author(2L, "Jane", "Smith", sampleBirthDate, "American", "A prolific writer.");
        assertNotEquals(author.hashCode(), differentAuthor.hashCode());
    }

    @Test
    void testHashCode_Consistency() {
        int initialHashCode = author.hashCode();
        assertEquals(initialHashCode, author.hashCode());
        author.setBiography("Changed bio"); // Should not affect hash code
        assertEquals(initialHashCode, author.hashCode());
    }

    @Test
    void testToString() {
        String expectedToString = "Author{" +
                "id=1" +
                ", firstName='John'" +
                ", lastName='Doe'" +
                ", birthDate=" + sampleBirthDate +
                ", nationality='American'" +
                ", biography='A prolific writer.'" +
                '}';
        assertEquals(expectedToString, author.toString());

        Author defaultAuthor = new Author();
        String expectedDefaultToString = "Author{" +
                "id=null" +
                ", firstName='null'" +
                ", lastName='null'" +
                ", birthDate=null" +
                ", nationality='null'" +
                ", biography='null'" +
                '}';
        assertEquals(expectedDefaultToString, defaultAuthor.toString());
    }
}