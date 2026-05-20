
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'MovieLensDB')
BEGIN
    CREATE DATABASE MovieLensDB;
END
GO

USE MovieLensDB;
GO

-- DROP existing tables (in FK-safe reverse order)
IF OBJECT_ID('dbo.genome_scores', 'U') IS NOT NULL DROP TABLE dbo.genome_scores;
IF OBJECT_ID('dbo.tags',          'U') IS NOT NULL DROP TABLE dbo.tags;
IF OBJECT_ID('dbo.ratings',       'U') IS NOT NULL DROP TABLE dbo.ratings;
IF OBJECT_ID('dbo.movie_genres',  'U') IS NOT NULL DROP TABLE dbo.movie_genres;
IF OBJECT_ID('dbo.links',         'U') IS NOT NULL DROP TABLE dbo.links;
IF OBJECT_ID('dbo.genome_tags',   'U') IS NOT NULL DROP TABLE dbo.genome_tags;
IF OBJECT_ID('dbo.genres',        'U') IS NOT NULL DROP TABLE dbo.genres;
IF OBJECT_ID('dbo.movies',        'U') IS NOT NULL DROP TABLE dbo.movies;
GO

-- TABLE: movies
CREATE TABLE dbo.movies (
    movieId      INT            NOT NULL,
    title        NVARCHAR(500)  NOT NULL,
    release_year SMALLINT       NULL,
    CONSTRAINT PK_movies PRIMARY KEY CLUSTERED (movieId)
);
GO

CREATE INDEX IX_movies_release_year ON dbo.movies (release_year);
GO

-- TABLE: genres  (master list)
CREATE TABLE dbo.genres (
    genreId   TINYINT        NOT NULL,
    genreName NVARCHAR(100)  NOT NULL,
    CONSTRAINT PK_genres PRIMARY KEY CLUSTERED (genreId),
    CONSTRAINT UQ_genres_name UNIQUE (genreName)
);
GO

-- TABLE: movie_genres  (many-to-many bridge)
CREATE TABLE dbo.movie_genres (
    movieId  INT     NOT NULL,
    genreId  TINYINT NOT NULL,
    CONSTRAINT PK_movie_genres PRIMARY KEY CLUSTERED (movieId, genreId),
    CONSTRAINT FK_movie_genres_movie  FOREIGN KEY (movieId)  REFERENCES dbo.movies (movieId),
    CONSTRAINT FK_movie_genres_genre  FOREIGN KEY (genreId)  REFERENCES dbo.genres (genreId)
);
GO

CREATE INDEX IX_movie_genres_genreId ON dbo.movie_genres (genreId);
GO

-- TABLE: links  (IMDB / TMDB cross-references)
CREATE TABLE dbo.links (
    movieId  INT            NOT NULL,
    imdbId   VARCHAR(20)    NULL,
    tmdbId   VARCHAR(20)    NULL,
    CONSTRAINT PK_links PRIMARY KEY CLUSTERED (movieId),
    CONSTRAINT FK_links_movie FOREIGN KEY (movieId) REFERENCES dbo.movies (movieId)
);
GO

-- TABLE: genome_tags
CREATE TABLE dbo.genome_tags (
    tagId  INT            NOT NULL,
    tag    NVARCHAR(500)  NOT NULL,
    CONSTRAINT PK_genome_tags PRIMARY KEY CLUSTERED (tagId)
);
GO

-- TABLE: genome_scores
CREATE TABLE dbo.genome_scores (
    movieId    INT            NOT NULL,
    tagId      INT            NOT NULL,
    relevance  DECIMAL(10,8)  NOT NULL,
    CONSTRAINT PK_genome_scores PRIMARY KEY CLUSTERED (movieId, tagId),
    CONSTRAINT FK_genome_scores_movie FOREIGN KEY (movieId) REFERENCES dbo.movies  (movieId),
    CONSTRAINT FK_genome_scores_tag   FOREIGN KEY (tagId)   REFERENCES dbo.genome_tags (tagId),
    CONSTRAINT CK_relevance CHECK (relevance BETWEEN 0.0 AND 1.0)
);
GO

CREATE INDEX IX_genome_scores_tagId ON dbo.genome_scores (tagId);
GO

-- TABLE: ratings
CREATE TABLE dbo.ratings (
    ratingId     BIGINT        IDENTITY(1,1) NOT NULL,
    userId       INT           NOT NULL,
    movieId      INT           NOT NULL,
    rating       DECIMAL(3,1)  NOT NULL,
    rating_date  DATETIME2     NOT NULL,
    CONSTRAINT PK_ratings  PRIMARY KEY CLUSTERED (ratingId),
    CONSTRAINT FK_ratings_movie  FOREIGN KEY (movieId)  REFERENCES dbo.movies (movieId),
    CONSTRAINT CK_rating_value   CHECK (rating BETWEEN 0.5 AND 5.0)
);
GO

CREATE INDEX IX_ratings_userId    ON dbo.ratings (userId);
CREATE INDEX IX_ratings_movieId   ON dbo.ratings (movieId);
CREATE INDEX IX_ratings_date      ON dbo.ratings (rating_date);
GO

-- TABLE: tags  (user-applied tags)
CREATE TABLE dbo.tags (
    tagId    BIGINT         IDENTITY(1,1) NOT NULL,
    userId   INT            NOT NULL,
    movieId  INT            NOT NULL,
    tag      NVARCHAR(500)  NOT NULL,
    tag_date DATETIME2      NOT NULL,
    CONSTRAINT PK_tags       PRIMARY KEY CLUSTERED (tagId),
    CONSTRAINT FK_tags_movie FOREIGN KEY (movieId) REFERENCES dbo.movies (movieId)
);
GO

CREATE INDEX IX_tags_movieId ON dbo.tags (movieId);
CREATE INDEX IX_tags_userId  ON dbo.tags (userId);
GO

-- SUMMARY VIEW  (convenient for analytics)
IF OBJECT_ID('dbo.vw_movie_stats', 'V') IS NOT NULL DROP VIEW dbo.vw_movie_stats;
GO

CREATE VIEW dbo.vw_movie_stats AS
SELECT
    m.movieId,
    m.title,
    m.release_year,
    COUNT(r.ratingId)          AS rating_count,
    AVG(CAST(r.rating AS FLOAT)) AS avg_rating,
    MIN(r.rating)              AS min_rating,
    MAX(r.rating)              AS max_rating
FROM dbo.movies m
LEFT JOIN dbo.ratings r ON r.movieId = m.movieId
GROUP BY m.movieId, m.title, m.release_year;
GO

