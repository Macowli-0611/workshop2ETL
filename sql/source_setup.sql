-- ==============================================================
-- DDL de Configuración de Fuente Operacional: Grammy Awards
-- Base de Datos: source_music_db (o esquema de origen)
-- ==============================================================

-- Eliminar tabla previa si existe para garantizar idempotencia en setup
DROP TABLE IF EXISTS grammy_awards CASCADE;

-- Crear tabla operacional para alojar los datos de Grammy Awards
CREATE TABLE grammy_awards (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    category VARCHAR(255) NOT NULL,
    nominee TEXT,
    artist TEXT,
    workers TEXT,
    img TEXT,
    winner BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices estratégicos para optimizar la extracción del pipeline
CREATE INDEX idx_grammy_year ON grammy_awards(year);
CREATE INDEX idx_grammy_category ON grammy_awards(category);
CREATE INDEX idx_grammy_artist ON grammy_awards(artist);
CREATE INDEX idx_grammy_winner ON grammy_awards(winner);

-- Comentarios explicativos de ingeniería
COMMENT ON TABLE grammy_awards IS 'Tabla operacional fuente de los premios Grammy, poblada inicialmente desde the_grammy_awards.csv para simular el origen relacional del pipeline.';
COMMENT ON COLUMN grammy_awards.winner IS 'Indica si el nominado ganó el premio en su respectiva categoría.';
