-- phpMyAdmin SQL Dump
-- version 3.4.0-dev
-- http://www.phpmyadmin.net
--
-- Host: 192.168.1.28:3306
-- Generation Time: Jan 22, 2011 at 02:19 AM
-- Server version: 5.0.51
-- PHP Version: 5.2.6-1+lenny9

SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Database: `tenticle`
--

-- --------------------------------------------------------

--
-- Table structure for table `copy_log`
--

CREATE TABLE IF NOT EXISTS `copy_log` (
  `id` int(255) NOT NULL auto_increment,
  `data` longtext NOT NULL,
  `time` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `downloaded_nzbs`
--

CREATE TABLE IF NOT EXISTS `downloaded_nzbs` (
  `id` int(255) NOT NULL auto_increment,
  `data` longtext NOT NULL,
  `time` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=7 ;

-- --------------------------------------------------------

--
-- Table structure for table `failed_copy`
--

CREATE TABLE IF NOT EXISTS `failed_copy` (
  `id` int(255) NOT NULL auto_increment,
  `data` longtext NOT NULL,
  `time` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `history`
--

CREATE TABLE IF NOT EXISTS `history` (
  `id` int(255) NOT NULL auto_increment,
  `time_stamp` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  `mesg` text NOT NULL,
  `catagory` varchar(255) NOT NULL,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=36 ;

-- --------------------------------------------------------

--
-- Table structure for table `raw_playlist`
--

CREATE TABLE IF NOT EXISTS `raw_playlist` (
  `id` int(255) NOT NULL auto_increment,
  `data` longtext NOT NULL,
  `time` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `settings`
--

CREATE TABLE IF NOT EXISTS `settings` (
  `id` int(255) NOT NULL auto_increment,
  `dn_flag` tinyint(4) NOT NULL,
  `scan_int` int(255) NOT NULL,
  `FAILED` varchar(255) NOT NULL,
  `shows_dir` varchar(255) NOT NULL,
  `dn_nzb_tmp` varchar(255) NOT NULL,
  `dn_dir` varchar(255) NOT NULL,
  `done_dir` varchar(255) NOT NULL,
  `faild_copy_log` varchar(255) NOT NULL,
  `copy_log` varchar(255) NOT NULL,
  `failed_file` varchar(255) NOT NULL,
  `failed_copy_file` varchar(255) NOT NULL,
  `shows_file` varchar(255) NOT NULL,
  `shows_details` varchar(255) NOT NULL,
  `shows_newest` varchar(255) NOT NULL,
  `downloaded_nzbs` varchar(255) NOT NULL,
  `raw_playlist` varchar(255) NOT NULL,
  `shows_playlist` varchar(255) NOT NULL,
  `NZB_USER` varchar(255) NOT NULL,
  `NZB_API_KEY` varchar(255) NOT NULL,
  `SAB_API_KEY` varchar(255) NOT NULL,
  `SAB_Host` varchar(255) NOT NULL,
  `SAB_Port` int(11) NOT NULL,
  `last_scan` int(255) NOT NULL,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=2 ;

-- --------------------------------------------------------

--
-- Table structure for table `shows_details`
--

CREATE TABLE IF NOT EXISTS `shows_details` (
  `id` int(255) NOT NULL auto_increment,
  `data` longtext NOT NULL,
  `time` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `shows_list`
--

CREATE TABLE IF NOT EXISTS `shows_list` (
  `id` int(255) NOT NULL auto_increment,
  `data` longtext NOT NULL,
  `time` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=5 ;

-- --------------------------------------------------------

--
-- Table structure for table `Shows_newest`
--

CREATE TABLE IF NOT EXISTS `Shows_newest` (
  `id` int(255) NOT NULL auto_increment,
  `data` longtext NOT NULL,
  `time` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=5 ;
