
package model;

import java.time.LocalDate;
import java.util.Objects;



public class Book {

    private Long id;
    private String title;
    private String isbn;
    private Author author;
    private String genre;
    private LocalDate publicationDate;
    private boolean available;
    private boolean lost;

    public Book() {
    }

    public Book(Long id, String title, String isbn, Author author, String genre, LocalDate publicationDate, boolean available, boolean lost) {
        this.id = id;
        this.title = title;
        this.isbn = isbn;
        this.author = author;
        this.genre = genre;
        this.publicationDate = publicationDate;
        this.available = available;
        this.lost = lost;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getIsbn() {
        return isbn;
    }

    public void setIsbn(String isbn) {
        this.isbn = isbn;
    }

    public Author getAuthor() {
        return author;
    }

    public void setAuthor(Author author) {
        this.author = author;
    }

    public String getGenre() {
        return genre;
    }

    public void setGenre(String genre) {
        this.genre = genre;
    }

    public LocalDate getPublicationDate() {
        return publicationDate;
    }

    public void setPublicationDate(LocalDate publicationDate) {
        this.publicationDate = publicationDate;
    }

    public boolean isAvailable() {
        return available;
    }

    public void setAvailable(boolean available) {
        this.available = available;
    }

    public boolean isLost() {
        return lost;
    }

    public void setLost(boolean lost) {
        this.lost = lost;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof Book)) {
            return false;
        }
        Book book = (Book) o;
        return Objects.equals(id, book.id) && Objects.equals(isbn, book.isbn);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, isbn);
    }

   
}
