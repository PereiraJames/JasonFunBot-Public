DROP TABLE IF EXISTS flights;

CREATE TABLE flights (
    id INT AUTO_INCREMENT PRIMARY KEY,

    date VARCHAR(20) NOT NULL,
    flightNo VARCHAR(20),
    sector VARCHAR(20),
    aircraft VARCHAR(20),
    duty VARCHAR(20),

    reportingTime VARCHAR(30),
    departureTime VARCHAR(30),
    arrivalTime VARCHAR(30),

    flightLength VARCHAR(20),

    reportHash CHAR(64) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_date (date),
    INDEX idx_flightNo (flightNo),
    INDEX idx_sector (sector),
    INDEX idx_duty (duty),
    INDEX idx_departureTime (departureTime)
);
