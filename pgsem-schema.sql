-- phpMyAdmin SQL Dump
-- version 2.7.0-pl2
-- http://www.phpmyadmin.net
-- 
-- Host: localhost
-- Generation Time: Mar 23, 2007 at 04:41 AM
-- Server version: 4.1.21
-- PHP Version: 4.4.4
-- 
-- Database: `pgsem`
-- 
CREATE DATABASE `pgsem` DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci;
USE pgsem;

-- --------------------------------------------------------

-- 
-- Table structure for table `authcode`
-- 

CREATE TABLE `authcode` (
  `rollno` varchar(7) NOT NULL default '',
  `authcode` varchar(20) NOT NULL default '',
  PRIMARY KEY  (`rollno`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

-- 
-- Table structure for table `changes`
-- 

CREATE TABLE `changes` (
  `rollno` varchar(7) NOT NULL default '',
  `request` varchar(50) NOT NULL default '',
  PRIMARY KEY  (`rollno`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

-- 
-- Table structure for table `choices`
-- 

CREATE TABLE `choices` (
  `rollno` varchar(7) NOT NULL default '',
  `priority` int(11) NOT NULL default '0',
  `ncourses` int(11) default NULL,
  `course` varchar(20) default NULL,
  `phaseonesubmitted` tinyint(1) default NULL,
  `project` tinyint(1) NOT NULL default '0',
  PRIMARY KEY  (`rollno`,`priority`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

-- 
-- Table structure for table `log`
-- 

CREATE TABLE `log` (
  `timestamp` varchar(20) NOT NULL default '',
  `msg` varchar(200) NOT NULL default ''
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
