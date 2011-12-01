
-- table defs

CREATE TABLE IF NOT EXISTS `users` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `username` varchar(255) NOT NULL,
    `password` varchar(255) NOT NULL,
    `email` varchar(255) DEFAULT NULL,
    `last_login` datetime DEFAULT NULL,
    `permission` int(1) DEFAULT 0,
    PRIMARY KEY(`id`),
    UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB;
    


CREATE TABLE IF NOT EXISTS `logs` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `type` varchar(255) DEFAULT NULL,
    `site` varchar(255) DEFAULT NULL,
    `text` text DEFAULT NULL,
    `datetime` datetime DEFAULT NULL,
    PRIMARY KEY(`id`),
    INDEX `site` (`site`),
    INDEX `type` (`type`)
) ENGINE=InnoDB;

create table IF NOT EXISTS sessions (
    session_id char(128) UNIQUE NOT NULL,
    atime timestamp NOT NULL default current_timestamp,
    data text
);

CREATE TABLE IF NOT EXISTS `mappings` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `site` varchar(255) NOT NULL,
    `branch` varchar(255) DEFAULT NULL,
    `changelist` int(11) NOT NULL,
    `datetime` datetime DEFAULT NULL,
    PRIMARY KEY(`id`),
    INDEX `site` (`site`)
) ENGINE=InnoDB;
    
    
