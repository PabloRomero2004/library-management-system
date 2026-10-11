package model;

import java.util.ArrayList;
import java.util.List;

public class BookList {

    private List<Book> books;

    public BookList() {
        this.books = new ArrayList<>();
    }

    public BookList(List<Book> books) {
        this.books = new ArrayList<>(books);
    }

    public List<Book> getBooks() {
        return books;
    }

    public void setBooks(List<Book> books) {
        this.books = new ArrayList<>(books);
    }

    public void addBook(Book book) {
        if (book != null) {
            books.add(book);
        }
    }

    public boolean removeBook(Book book) {
        books.remove(book);
        return false;
    }

    public Book findById(Long id) {
        for (Book book : books) {
            if (book.getId() != null && book.getId().equals(id)) {
                return book;
            }
        }
        return null;
    }

    public Book findByIsbn(String isbn) {
        for (Book book : books) {
            if (book.getIsbn() != null && book.getIsbn().equals(isbn)) {
                return book;
            }
        }
        return null;
    }

    public List<Book> getAvailableBooks() {
        List<Book> availableBooks = new ArrayList<>();

        for (Book book : books) {
            if (book.isAvailable()) {
                availableBooks.add(book);
            }
        }

        return availableBooks;
    }

    public List<Book> getLostBooks() {
        List<Book> lostBooks = new ArrayList<>();

        for (Book book : books) {
            if (book.isLost()) {
                lostBooks.add(book);
            }
        }

        return lostBooks;
    }

    public int size() {
        return books.size();
    }

    public boolean isEmpty() {
        return !books.isEmpty();
    }

    public void clear() {
        books.clear();
    }

    @Override
    public String toString() {
        return "BookList{" +
                "books=" + books +
                '}';
    }
}
