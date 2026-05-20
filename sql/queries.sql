USE MovieLensDB;
GO

-- Q1: Top 20 Highest Rated Movies (min 500 ratings)
SELECT TOP 20
    m.movieId,
    m.title,
    m.release_year,
    COUNT(r.ratingId)              AS total_ratings,
    ROUND(AVG(CAST(r.rating AS FLOAT)), 3) AS avg_rating,
    STDEV(CAST(r.rating AS FLOAT)) AS rating_stddev
FROM dbo.movies m
JOIN dbo.ratings r ON r.movieId = m.movieId
GROUP BY m.movieId, m.title, m.release_year
HAVING COUNT(r.ratingId) >= 500
ORDER BY avg_rating DESC, total_ratings DESC;
GO

-- Q2: Most Active Users (Top 30 by number of ratings)
SELECT TOP 30
    userId,
    COUNT(*)                              AS total_ratings,
    ROUND(AVG(CAST(rating AS FLOAT)), 3)  AS avg_rating,
    MIN(rating)                           AS min_rating,
    MAX(rating)                           AS max_rating,
    MIN(rating_date)                      AS first_rating_date,
    MAX(rating_date)                      AS last_rating_date,
    DATEDIFF(DAY, MIN(rating_date), MAX(rating_date)) AS active_days
FROM dbo.ratings
GROUP BY userId
ORDER BY total_ratings DESC;
GO

-- Q3: Rating Trends by Year
SELECT
    YEAR(rating_date)                        AS rating_year,
    COUNT(*)                                 AS total_ratings,
    ROUND(AVG(CAST(rating AS FLOAT)), 3)     AS avg_rating,
    COUNT(DISTINCT userId)                   AS distinct_users,
    COUNT(DISTINCT movieId)                  AS distinct_movies
FROM dbo.ratings
GROUP BY YEAR(rating_date)
ORDER BY rating_year;
GO

-- Q4: Most Popular Genres by Number of Ratings
SELECT
    g.genreName,
    COUNT(r.ratingId)                        AS total_ratings,
    COUNT(DISTINCT r.userId)                 AS distinct_users,
    COUNT(DISTINCT m.movieId)                AS movie_count,
    ROUND(AVG(CAST(r.rating AS FLOAT)), 3)   AS avg_rating
FROM dbo.genres g
JOIN dbo.movie_genres mg ON mg.genreId = g.genreId
JOIN dbo.movies       m  ON m.movieId  = mg.movieId
JOIN dbo.ratings      r  ON r.movieId  = m.movieId
GROUP BY g.genreName
ORDER BY total_ratings DESC;
GO

-- Q5: Genre-Based Average Ratings (ranked)
WITH genre_stats AS (
    SELECT
        g.genreName,
        COUNT(r.ratingId)                      AS total_ratings,
        AVG(CAST(r.rating AS FLOAT))           AS avg_rating
    FROM dbo.genres g
    JOIN dbo.movie_genres mg ON mg.genreId = g.genreId
    JOIN dbo.ratings       r ON r.movieId  = mg.movieId
    GROUP BY g.genreName
)
SELECT
    genreName,
    total_ratings,
    ROUND(avg_rating, 3) AS avg_rating,
    RANK() OVER (ORDER BY avg_rating DESC) AS rank_by_rating
FROM genre_stats
ORDER BY avg_rating DESC;
GO

-- Q6: Top 10 Movies by Number of Ratings (popularity)
SELECT TOP 10
    m.movieId,
    m.title,
    m.release_year,
    COUNT(r.ratingId)                       AS total_ratings,
    ROUND(AVG(CAST(r.rating AS FLOAT)), 3)  AS avg_rating
FROM dbo.movies m
JOIN dbo.ratings r ON r.movieId = m.movieId
GROUP BY m.movieId, m.title, m.release_year
ORDER BY total_ratings DESC;
GO

-- Q7: User Activity Analytics – Rating Distribution
SELECT
    rating,
    COUNT(*) AS frequency,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM dbo.ratings
GROUP BY rating
ORDER BY rating;
GO

-- Q8: Monthly Rating Volume (last 5 years of data)
SELECT
    YEAR(rating_date)  AS yr,
    MONTH(rating_date) AS mo,
    COUNT(*)           AS ratings_count,
    ROUND(AVG(CAST(rating AS FLOAT)), 3) AS avg_rating
FROM dbo.ratings
WHERE rating_date >= DATEADD(YEAR, -5, GETDATE())
GROUP BY YEAR(rating_date), MONTH(rating_date)
ORDER BY yr, mo;
GO

-- Q9: Top Tags per Movie (most-applied tags)
SELECT TOP 50
    m.title,
    t.tag,
    COUNT(*) AS tag_count
FROM dbo.tags t
JOIN dbo.movies m ON m.movieId = t.movieId
GROUP BY m.title, t.tag
ORDER BY tag_count DESC;
GO

-- Q10: Movies with No Ratings (orphaned)
SELECT
    m.movieId,
    m.title,
    m.release_year
FROM dbo.movies m
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.ratings r WHERE r.movieId = m.movieId
)
ORDER BY m.release_year DESC;
GO

-- Q11: Window Function – Rolling Average Rating per Movie per Year
WITH yearly AS (
    SELECT
        m.movieId,
        m.title,
        YEAR(r.rating_date)                  AS yr,
        AVG(CAST(r.rating AS FLOAT))         AS yr_avg,
        COUNT(r.ratingId)                    AS yr_count
    FROM dbo.ratings r
    JOIN dbo.movies  m ON m.movieId = r.movieId
    GROUP BY m.movieId, m.title, YEAR(r.rating_date)
)
SELECT
    movieId,
    title,
    yr,
    yr_avg,
    yr_count,
    AVG(yr_avg) OVER (
        PARTITION BY movieId
        ORDER BY yr
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS rolling_3yr_avg
FROM yearly
ORDER BY movieId, yr;
GO

-- Q12: Genre Combinations – Most Common Multi-Genre Pairs
SELECT TOP 20
    g1.genreName AS genre1,
    g2.genreName AS genre2,
    COUNT(DISTINCT mg1.movieId) AS movie_count
FROM dbo.movie_genres mg1
JOIN dbo.movie_genres mg2 ON mg2.movieId = mg1.movieId AND mg2.genreId > mg1.genreId
JOIN dbo.genres       g1  ON g1.genreId  = mg1.genreId
JOIN dbo.genres       g2  ON g2.genreId  = mg2.genreId
GROUP BY g1.genreName, g2.genreName
ORDER BY movie_count DESC;
GO

-- Q13: Highly Relevant Genome Tags per Movie (Top Tags)
SELECT TOP 30
    m.title,
    gt.tag,
    gs.relevance
FROM dbo.genome_scores gs
JOIN dbo.movies      m  ON m.movieId  = gs.movieId
JOIN dbo.genome_tags gt ON gt.tagId   = gs.tagId
WHERE gs.relevance >= 0.8
ORDER BY gs.relevance DESC;
GO

-- Q14: Decade Analysis – Average Rating by Release Decade
SELECT
    (release_year / 10) * 10        AS decade,
    COUNT(DISTINCT m.movieId)       AS movie_count,
    COUNT(r.ratingId)               AS total_ratings,
    ROUND(AVG(CAST(r.rating AS FLOAT)), 3) AS avg_rating
FROM dbo.movies m
JOIN dbo.ratings r ON r.movieId = m.movieId
WHERE m.release_year IS NOT NULL
GROUP BY (release_year / 10) * 10
ORDER BY decade;
GO

-- Q15: User Loyalty – Users who rated across the most genres
SELECT TOP 20
    r.userId,
    COUNT(DISTINCT g.genreId)    AS distinct_genres,
    COUNT(r.ratingId)            AS total_ratings,
    ROUND(AVG(CAST(r.rating AS FLOAT)), 3) AS avg_rating
FROM dbo.ratings      r
JOIN dbo.movie_genres mg ON mg.movieId = r.movieId
JOIN dbo.genres       g  ON g.genreId  = mg.genreId
GROUP BY r.userId
ORDER BY distinct_genres DESC, total_ratings DESC;
GO
