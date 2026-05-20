USE MovieLensDB;
GO

-- Verify row counts after ETL load
SELECT 'movies'        AS tbl, COUNT(*) AS rows FROM dbo.movies        UNION ALL
SELECT 'genres'        AS tbl, COUNT(*) AS rows FROM dbo.genres        UNION ALL
SELECT 'movie_genres'  AS tbl, COUNT(*) AS rows FROM dbo.movie_genres  UNION ALL
SELECT 'ratings'       AS tbl, COUNT(*) AS rows FROM dbo.ratings       UNION ALL
SELECT 'tags'          AS tbl, COUNT(*) AS rows FROM dbo.tags          UNION ALL
SELECT 'links'         AS tbl, COUNT(*) AS rows FROM dbo.links         UNION ALL
SELECT 'genome_tags'   AS tbl, COUNT(*) AS rows FROM dbo.genome_tags   UNION ALL
SELECT 'genome_scores' AS tbl, COUNT(*) AS rows FROM dbo.genome_scores;
GO

-- Quick top-5 most-rated movies as test
SELECT TOP 5
    m.title,
    COUNT(*) AS cnt,
    AVG(CAST(r.rating AS FLOAT)) AS avg_rt
FROM dbo.ratings r
JOIN dbo.movies m ON m.movieId = r.movieId
GROUP BY m.title
ORDER BY cnt DESC;
GO
