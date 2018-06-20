ALTER TABLE users ADD COLUMN hustler_points FLOAT NOT NULL DEFAULT 0; 
ALTER TABLE users ADD COLUMN hustler_correct_bets INT NOT NULL DEFAULT 0; 
ALTER TABLE users ADD COLUMN gambler_points FLOAT NOT NULL DEFAULT 0; 
ALTER TABLE users ADD COLUMN expert_points FLOAT NOT NULL DEFAULT 0; 
ALTER TABLE users ADD COLUMN expert_team_id INT;
ALTER TABLE users ADD COLUMN hattrick_points FLOAT NOT NULL DEFAULT 0; 

ALTER TABLE users ADD CONSTRAINT users_ibfk_2 FOREIGN KEY (expert_team_id) REFERENCES teams(id);

