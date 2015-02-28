-- PostgreSQL SQL Dump

--
-- Database: tenticle
--
CREATE SEQUENCE ai_seq;
-- --------------------------------------------------------

--
-- Table structure for table copy_log
--

CREATE TABLE copy_log (
  id integer default nextval('ai_seq') primary key,
  data text[] NOT NULL,
  time integer NOT NULL
);

--
-- Dumping data for table copy_log
--


-- --------------------------------------------------------

--
-- Table structure for table downloaded_nzbs
--

CREATE TABLE downloaded_nzbs (
  id integer default nextval('ai_seq') primary key,
  data text[] NOT NULL,
  time integer NOT NULL
);

--
-- Dumping data for table downloaded_nzbs
--


-- --------------------------------------------------------

--
-- Table structure for table failed_copy
--

CREATE TABLE failed_copy (
  id integer default nextval('ai_seq') primary key,
  data text[] NOT NULL,
  time integer NOT NULL
);

--
-- Dumping data for table failed_copy
--


-- --------------------------------------------------------

--
-- Table structure for table history
--

CREATE TABLE history (
  id integer default nextval('ai_seq') primary key,
  time_stamp integer NOT NULL,
  mesg text NOT NULL,
  catagory text NOT NULL
);

--
-- Dumping data for table history
--


-- --------------------------------------------------------

--
-- Table structure for table raw_playlist
--

CREATE TABLE raw_playlist (
  id integer default nextval('ai_seq') primary key,
  data text[] NOT NULL,
  time integer NOT NULL
);

--
-- Dumping data for table raw_playlist
--


-- --------------------------------------------------------

--
-- Table structure for table settings
--

CREATE TABLE settings (
  id integer default nextval('ai_seq') primary key,
  dn_flag integer NOT NULL,
  scan_int int NOT NULL,
  FAILED text NOT NULL,
  shows_dir text NOT NULL,
  dn_nzb_tmp text NOT NULL,
  dn_dir text NOT NULL,
  done_dir text NOT NULL,
  faild_copy_log text NOT NULL,
  copy_log text NOT NULL,
  failed_file text NOT NULL,
  failed_copy_file text NOT NULL,
  shows_file text NOT NULL,
  shows_details text NOT NULL,
  shows_newest text NOT NULL,
  downloaded_nzbs text NOT NULL,
  raw_playlist text NOT NULL,
  shows_playlist text NOT NULL,
  NZB_USER text NOT NULL,
  NZB_API_KEY text NOT NULL,
  SAB_API_KEY text NOT NULL,
  SAB_Host text NOT NULL,
  SAB_Port integer NOT NULL,
  last_scan int NOT NULL
);

INSERT INTO settings (id, dn_flag, scan_int, FAILED, shows_dir, dn_nzb_tmp, dn_dir, done_dir, faild_copy_log, copy_log, failed_file, failed_copy_file, shows_file, shows_details, shows_newest, downloaded_nzbs, raw_playlist, shows_playlist, NZB_USER, NZB_API_KEY, SAB_API_KEY, SAB_Host, SAB_Port, last_scan) VALUES
(1, 1, 9000, '_FAILED_', '/mnt/media/Shows/', '/mnt/data/NZB_TMP/', '/mnt/temp/NZB_AutoDownload/', '/mnt/temp/NZB_Finished_Unsorted/', 'failed_copy', 'copy_log', 'failed_copy', 'failed_copy', 'shows_list', 'shows_details', 'Shows_newest', 'downloaded_nzbs', 'raw_playlist', '/mnt/media/Shows.asx', 'pferland', 'aa3a69669a953930ef86c281bd5abc64', '6ac7b38a79c9a6158ddaf5c8e2a02788', '192.168.1.15', 8080, 1295934020);

-- --------------------------------------------------------

--
-- Table structure for table shows_details
--

CREATE TABLE shows_details (
  id integer default nextval('ai_seq') primary key,
  data text[] NOT NULL,
  time integer NOT NULL
  
);

-- --------------------------------------------------------

--
-- Table structure for table shows_list
--

CREATE TABLE shows_list (
  id integer default nextval('ai_seq') primary key,
  data text[] NOT NULL,
  time integer NOT NULL
  
);

-- --------------------------------------------------------

--
-- Table structure for table Shows_newest
--

CREATE TABLE Shows_newest (
  id integer default nextval('ai_seq') primary key,
  data text[] NOT NULL,
  time integer NOT NULL
  
);