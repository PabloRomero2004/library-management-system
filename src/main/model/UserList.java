package model;

import java.util.ArrayList;
import java.util.List;

public class UserList {

    private List<User> users;

    public UserList() {
        this.users = new ArrayList<>();
    }

    public UserList(List<User> users) {
        this.users = new ArrayList<>(users);
    }

    public List<User> getUsers() {
        return new ArrayList<>(users);
    }

    public void setUsers(List<User> users) {
        this.users = new ArrayList<>(users);
    }

    // Añadir un usuario
    public void addUser(User user) {
        if (user != null && !users.contains(user)) {
            users.add(user);
        }
    }

    // Eliminar un usuario
    public boolean removeUser(User user) {
        return users.remove(user);
    }

    // Buscar usuario por ID
    public User findById(Long id) {
        for (User user : users) {
            if (user.getId() != null && user.getId().equals(id)) {
                return user;
            }
        }
        return null;
    }

    // Buscar usuario por email
    public User findByEmail(String email) {
        for (User user : users) {
            if (user.getEmail() != null &&
                    user.getEmail().equalsIgnoreCase(email)) {
                return user;
            }
        }
        return null;
    }

    // Obtener usuarios activos
    public List<User> getActiveUsers() {
        List<User> activeUsers = new ArrayList<>();

        for (User user : users) {
            if (user.isActive()) {
                activeUsers.add(user);
            }
        }

        return activeUsers;
    }

    // Número total de usuarios
    public int size() {
        return users.size();
    }

    // Comprobar si está vacía
    public boolean isEmpty() {
        return users.isEmpty();
    }

    // Eliminar todos los usuarios
    public void clear() {
        users.clear();
    }

    @Override
    public String toString() {
        return "UserList{" +
                "users=" + users +
                '}';
    }
}