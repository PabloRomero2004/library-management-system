package model;

import org.junit.jupiter.api.Test;

import model.User;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.*;

class UserTest {

    @Test
    void shouldCreateUserWithDefaultConstructor() {
        User user = new User();

        assertNull(user.getId());
        assertNull(user.getFirstName());
        assertNull(user.getLastName());
        assertNull(user.getEmail());
        assertNull(user.getLibraryCardNumber());
        assertNull(user.getRegistrationDate());
        assertFalse(user.isActive());
    }

    @Test
    void shouldCreateUserWithAllArgumentsConstructor() {
        LocalDate registrationDate = LocalDate.of(2025, 1, 1);

        User user = new User(
                1L,
                "John",
                "Doe",
                "john.doe@test.com",
                "CARD001",
                registrationDate,
                true
        );

        assertEquals(1L, user.getId());
        assertEquals("John", user.getFirstName());
        assertEquals("Doe", user.getLastName());
        assertEquals("john.doe@test.com", user.getEmail());
        assertEquals("CARD001", user.getLibraryCardNumber());
        assertEquals(registrationDate, user.getRegistrationDate());
        assertTrue(user.isActive());
    }

    @Test
    void shouldSetAndGetAllFields() {
        LocalDate registrationDate = LocalDate.now();

        User user = new User();

        user.setId(10L);
        user.setFirstName("Alice");
        user.setLastName("Smith");
        user.setEmail("alice@test.com");
        user.setLibraryCardNumber("CARD999");
        user.setRegistrationDate(registrationDate);
        user.setActive(true);

        assertEquals(10L, user.getId());
        assertEquals("Alice", user.getFirstName());
        assertEquals("Smith", user.getLastName());
        assertEquals("alice@test.com", user.getEmail());
        assertEquals("CARD999", user.getLibraryCardNumber());
        assertEquals(registrationDate, user.getRegistrationDate());
        assertTrue(user.isActive());
    }

    @Test
    void shouldReturnFullName() {
        User user = new User();
        user.setFirstName("John");
        user.setLastName("Doe");

        assertEquals("John Doe", user.getFullName());
    }

    @Test
    void shouldReturnOnlyFirstNameWhenLastNameIsEmpty() {
        User user = new User();
        user.setFirstName("John");
        user.setLastName("");

        assertEquals("John", user.getFullName());
    }

    @Test
    void shouldBeEqualWhenIdAndEmailAreEqual() {
        User user1 = new User(
                1L,
                "John",
                "Doe",
                "john@test.com",
                "CARD001",
                LocalDate.now(),
                true
        );

        User user2 = new User(
                1L,
                "Another",
                "User",
                "john@test.com",
                "CARD999",
                LocalDate.now(),
                false
        );

        assertEquals(user1, user2);
    }

    @Test
    void shouldNotBeEqualWhenIdIsDifferent() {
        User user1 = new User(
                1L,
                "John",
                "Doe",
                "john@test.com",
                "CARD001",
                LocalDate.now(),
                true
        );

        User user2 = new User(
                2L,
                "John",
                "Doe",
                "john@test.com",
                "CARD001",
                LocalDate.now(),
                true
        );

        assertNotEquals(user1, user2);
    }

    @Test
    void shouldNotBeEqualWhenEmailIsDifferent() {
        User user1 = new User(
                1L,
                "John",
                "Doe",
                "john1@test.com",
                "CARD001",
                LocalDate.now(),
                true
        );

        User user2 = new User(
                1L,
                "John",
                "Doe",
                "john2@test.com",
                "CARD001",
                LocalDate.now(),
                true
        );

        assertNotEquals(user1, user2);
    }

    @Test
    void shouldHaveSameHashCodeWhenObjectsAreEqual() {
        User user1 = new User(
                1L,
                "John",
                "Doe",
                "john@test.com",
                "CARD001",
                LocalDate.now(),
                true
        );

        User user2 = new User(
                1L,
                "Other",
                "User",
                "john@test.com",
                "CARD002",
                LocalDate.now(),
                false
        );

        assertEquals(user1.hashCode(), user2.hashCode());
    }

    @Test
    void shouldNotBeEqualToNull() {
        User user = new User();

        assertNotEquals(null, user);
    }

    @Test
    void shouldNotBeEqualToDifferentClass() {
        User user = new User();

        assertNotEquals("test", user);
    }

    @Test
    void shouldContainImportantFieldsInToString() {
        User user = new User(
                1L,
                "John",
                "Doe",
                "john@test.com",
                "CARD001",
                LocalDate.of(2025, 1, 1),
                true
        );

        String result = user.toString();

        assertTrue(result.contains("John"));
        assertTrue(result.contains("Doe"));
        assertTrue(result.contains("john@test.com"));
        assertTrue(result.contains("CARD001"));
    }
}