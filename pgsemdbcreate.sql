

CREATE TABLE `authcode` (
  `rollno` varchar(7) NOT NULL default '',
  `authcode` varchar(20) NOT NULL default '',
  PRIMARY KEY  (`rollno`)
) TYPE=MyISAM;

CREATE TABLE `changes` (
  `rollno` varchar(7) NOT NULL default '',
  `request` varchar(50) NOT NULL default '',
  PRIMARY KEY  (`rollno`)
) TYPE=MyISAM;

CREATE TABLE `choices` (
  `rollno` varchar(7) NOT NULL default '',
  `priority` int(11) NOT NULL default '0',
  `ncourses` int(11) default NULL,
  `course` varchar(20) default NULL,
  `phaseonesubmitted` tinyint(1) default NULL,
  PRIMARY KEY  (`rollno`,`priority`)
) TYPE=MyISAM;

CREATE TABLE `log` (
  `timestamp` varchar(20) NOT NULL default '',
  `msg` varchar(200) NOT NULL default ''
) TYPE=MyISAM;

-- end of file
