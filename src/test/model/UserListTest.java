package model;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class UserListTest {

    private UserList userList;
    private User user1;
    private User user2;
    private User user3;

    @BeforeEach
    void setUp() {
        user1 = new User(1L, "John", "Doe", "john.doe@example.com", "LC001", LocalDate.now(), true);
        user2 = new User(2L, "Jane", "Smith", "jane.smith@example.com", "LC002", LocalDate.now(), false);
        user3 = new User(3L, "Peter", "Jones", "peter.jones@example.com", "LC003", LocalDate.now(), true);
        userList = new UserList();
    }

    @Test
    void testUserListDefaultConstructor() {
        assertNotNull(userList);
        assertTrue(userList.isEmpty());
        assertEquals(0, userList.size());
    }

    @Test
    void testUserListParameterizedConstructor() {
        List<User> initialUsers = new ArrayList<>(Arrays.asList(user1, user2));
        UserList populatedUserList = new UserList(initialUsers);

        assertNotNull(populatedUserList);
        assertFalse(populatedUserList.isEmpty());
        assertEquals(2, populatedUserList.size());
        assertTrue(populatedUserList.getUsers().contains(user1));
        assertTrue(populatedUserList.getUsers().contains(user2));

        // Test defensive copy
        initialUsers.add(user3);
        assertEquals(2, populatedUserList.size(), "Modifying original list should not affect UserList");
    }

    @Test
    void testGetUsers() {
        userList.addUser(user1);
        userList.addUser(user2);

        List<User> retrievedUsers = userList.getUsers();
        assertNotNull(retrievedUsers);
        assertEquals(2, retrievedUsers.size());
        assertTrue(retrievedUsers.contains(user1));
        assertTrue(retrievedUsers.contains(user2));

        // Test defensive copy
        retrievedUsers.add(user3);
        assertEquals(2, userList.size(), "Modifying returned list should not affect internal list");
    }

    @Test
    void testSetUsers() {
        List<User> newUsers = new ArrayList<>(Arrays.asList(user1, user3));
        userList.setUsers(newUsers);

        assertEquals(2, userList.size());
        assertTrue(userList.getUsers().contains(user1));
        assertTrue(userList.getUsers().contains(user3));
        assertFalse(userList.getUsers().contains(user2));

        // Test defensive copy
        newUsers.add(user2);
        assertEquals(2, userList.size(), "Modifying original list after set should not affect UserList");

        // Test setting with an empty list
        userList.setUsers(Collections.emptyList());
        assertTrue(userList.isEmpty());
    }

    @Test
    void testAddUser() {
        userList.addUser(user1);
        assertEquals(1, userList.size());
        assertTrue(userList.getUsers().contains(user1));

        // Add another user
        userList.addUser(user2);
        assertEquals(2, userList.size());
        assertTrue(userList.getUsers().contains(user2));

        // Add null user
        userList.addUser(null);
        assertEquals(2, userList.size(), "Adding null user should not change size");

        // Add existing user (should not add duplicate based on equals/hashCode)
        userList.addUser(user1);
        assertEquals(2, userList.size(), "Adding existing user should not change size");
    }

    @Test
    void testRemoveUser() {
        userList.addUser(user1);
        userList.addUser(user2);
        assertEquals(2, userList.size());

        // Remove existing user
        assertTrue(userList.removeUser(user1));
        assertEquals(1, userList.size());
        assertFalse(userList.getUsers().contains(user1));

        // Remove non-existing user
        assertFalse(userList.removeUser(user3));
        assertEquals(1, userList.size());

        // Remove null user
        assertFalse(userList.removeUser(null));
        assertEquals(1, userList.size());

        // Remove the last user
        assertTrue(userList.removeUser(user2));
        assertTrue(userList.isEmpty());
    }

    @Test
    void testFindById() {
        userList.addUser(user1);
        userList.addUser(user2);

        // Find existing user
        assertEquals(user1, userList.findById(1L));
        assertEquals(user2, userList.findById(2L));

        // Find non-existing user
        assertNull(userList.findById(99L));

        // Find with null ID
        assertNull(userList.findById(null));

        // Test user with null ID in the list (should not be found by ID)
        User userWithNullId = new User(null, "Test", "User", "test@example.com", "LC004", LocalDate.now(), true);
        userList.addUser(userWithNullId);
        assertNull(userList.findById(null)); // Should not find userWithNullId by searching for null ID
        assertNull(userList.findById(4L)); // Should not find userWithNullId by searching for a specific ID
    }

    @Test
    void testFindByEmail() {
        userList.addUser(user1); // john.doe@example.com
        userList.addUser(user2); // jane.smith@example.com

        // Find existing user (case-insensitive)
        assertEquals(user1, userList.findByEmail("john.doe@example.com"));
        assertEquals(user1, userList.findByEmail("JOHN.DOE@EXAMPLE.COM"));
        assertEquals(user2, userList.findByEmail("jane.smith@example.com"));

        // Find non-existing user
        assertNull(userList.findByEmail("nonexistent@example.com"));

        // Find with null email
        assertNull(userList.findByEmail(null));

        // Test user with null email in the list (should not be found by email)
        User userWithNullEmail = new User(4L, "Test", "User", null, "LC004", LocalDate.now(), true);
        userList.addUser(userWithNullEmail);
        assertNull(userList.findByEmail("test@example.com")); // Should not find userWithNullEmail
        assertNull(userList.findByEmail(null)); // Should not find userWithNullEmail
    }

    @Test
    void testGetActiveUsers() {
        userList.addUser(user1); // active
        userList.addUser(user2); // inactive
        userList.addUser(user3); // active

        List<User> activeUsers = userList.getActiveUsers();
        assertNotNull(activeUsers);
        assertEquals(2, activeUsers.size());
        assertTrue(activeUsers.contains(user1));
        assertTrue(activeUsers.contains(user3));
        assertFalse(activeUsers.contains(user2));

        // Test when no active users
        userList.clear();
        userList.addUser(user2); // inactive
        activeUsers = userList.getActiveUsers();
        assertTrue(activeUsers.isEmpty());

        // Test when list is empty
        userList.clear();
        activeUsers = userList.getActiveUsers();
        assertTrue(activeUsers.isEmpty());

        // Test defensive copy
        activeUsers.add(user1);
        assertEquals(0, userList.getActiveUsers().size(), "Modifying returned list should not affect internal list");
    }

    @Test
    void testSize() {
        assertEquals(0, userList.size());

        userList.addUser(user1);
        assertEquals(1, userList.size());

        userList.addUser(user2);
        assertEquals(2, userList.size());

        userList.removeUser(user1);
        assertEquals(1, userList.size());

        userList.clear();
        assertEquals(0, userList.size());
    }

    @Test
    void testIsEmpty() {
        assertTrue(userList.isEmpty());

        userList.addUser(user1);
        assertFalse(userList.isEmpty());

        userList.removeUser(user1);
        assertTrue(userList.isEmpty());
    }

    @Test
    void testClear() {
        userList.addUser(user1);
        userList.addUser(user2);
        assertFalse(userList.isEmpty());

        userList.clear();
        assertTrue(userList.isEmpty());
        assertEquals(0, userList.size());
    }

    @Test
    void testToString() {
        userList.addUser(user1);
        userList.addUser(user2);
        String expectedToString = "UserList{users=" + Arrays.asList(user1, user2) + "}";
        assertEquals(expectedToString, userList.toString());

        userList.clear();
        expectedToString = "UserList{users=[]}";
        assertEquals(expectedToString, userList.toString());
    }
}