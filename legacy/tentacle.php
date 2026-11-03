<?php
error_reporting(E_ALL&E_STRICT);
#    tentacle.php, The SABnzbd Usenet TV Show downloader and sorter. Pretty Crappy Edition.
#    Copyright (C) 2010
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License v2 as published by
#    the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
###############################
##     _  _(o)_(o)_  _       ##
##   ._\`:_ F S M _:' \_,    ##
##       / (`---'\ `-.       ##
##    ,-`  _)    (_,         ##
###############################


$tentacle = new tentacle($argv);
$tentacle->main_loop();

###### Class
class tentacle
{
    function  __construct($argv)
    {
        #### Default Values
        $this->ver = "3.0";
        $this->last_edit = "2011-01-20";
        $this->sep = DIRECTORY_SEPARATOR;
        $this->args=array();
        $this->settings=array();
        $this->shows_array=array();
        $this->playlist_array=array();
        $this->shows_details=array();
        $this->types=array();
        $this->recover = 0;
        $this->downloaded=array();
        $this->failed_copy=array();
        $this->coped=array();
		$this->newest_files=array();
		$this->name="";
		$this->rm_cmd="rm -rf";
		$this->skipto="";
		$this->desc = " tentacle Searches your Media directory for supported files,
			generates a playlist of all the files, and will update still
			running shows with the newest eppisodes automatically.
		This Version is controled from a web interface driven by a SQL backend.";

			#load config file for SQL settings
			$this->pars_args($argv);
			if(@$this->args['config'])
			{
				include($this->args['config']);
				$this->__set('settings', array_merge(array(), $default));
				$this->__set('sql_settings_file', $this->args['config']);
			}elseif(@$this->args['c'])
		{
			include($this->args['c']);
				$this->__set('settings', array_merge(array(), $default));
				$this->__set('sql_settings_file', $this->args['c']);
		}else
			{
				include('settings/shows_sql.php');
				$this->__set('settings', array_merge(array(), $default));
				$this->__set('sql_settings_file', 'settings/shows_sql.php');
			}

		### SQL Override values
		## Set SQL DB name from CLI Argument
		if(@$this->args['g'])
			{
				$this->settings['db'] = $this->args['g'];
			}elseif(@$this->args['db'])
		{
			$this->settings['db'] = $this->args['db'];
		}
		## Set SQL host from CLI Argument
		if(@$this->args['q'])
			{
				$this->settings['sqlhost'] = $this->args['q'];
			}elseif(@$this->args['sqlhost'])
		{
			$this->settings['sqlhost'] = $this->args['sqlhost'];
		}
		## Set SQL User from CLI Argument, and then ask for the password
		if(@$this->args['y'])
			{
				$this->settings['sqluser'] = $this->args['y'];
			
				$this->settings['sqlpwd'] = get_pwd();
			}elseif(@$this->args['sqluser'])
		{
			$this->settings['sqluser'] = $this->args['sqluser'];

			$this->settings['sqlpwd'] = get_pwd();
		}
			define('SQL_TYPE', $this->settings['sqlhosttype']);
			define('SQL_HOST', $this->settings['sqlhost']);
			define('SQL_USER', $this->settings['sqluser']);
			define('SQL_PWD', $this->settings['sqlpwd']);
			define('SQL_DB', $this->settings['db']);

			if(@$this->args['verbose']===true||@$this->args['v']===true)
			{$this->verbose=1;echo "Verbose Mode\r\n";}else{$this->verbose=0;}


			if(@$this->args['run_once'])
			{
				$this->run_once=1;
				if($this->verbose){echo "Run Once Mode\r\n";}
			}else
			{
				$this->run_once=0;
				if($this->verbose){echo "Daemon Mode\r\n\r\n";}
			}

		if(@$this->args['n'])
			{
				$this->nzb_sleep = $this->args['n'];
			}elseif(@$this->args['nzb-sleep'])
		{
			$this->nzb_sleep = $this->args['nzb-sleep'];
		}else
		{
			$this->nzb_sleep = 10;
		}
		if($this->verbose){echo "NZB Matrix Sleep period: $this->nzb_sleep\r\n";}


		if(@$this->args['s'])
		{
				$this->skipto = $this->args['s'];
		}
		elseif(@$this->args['skipto'])
		{
			$this->skipto = $this->args['skipto'];
		}

			## Got all the SQL settings, lets compile the Settings var now.
		$this->GetSQLSettings();
    }
	
    function __set($name, $value)
    {
        $this->$name = $value;
    }
    
	function main_loop()
    {
        $this->checks();
	echo "tentacle v$this->ver\r\nLast Edit: ".$this->last_edit."\r\nBy: Longbow486\r\n\r\n";
        $this->log_write("tentacle is now running...","audit");
        while(1)
        {
            $this->check_shows_array();

            $this->log_write("Running File Type Stats...","audit");
            $this->run_file_type_stats();

            if($this->verbose){echo "Compiling Newest Episode lists:\r\n";}
            $this->log_write("Compiling Newest Episode list...","audit");
            $this->newest_files = $this->get_newest_files($this->shows_array);

            if($this->verbose){echo "Writing Newest Episodes data to file (".  $this->settings['shows_newest'].")\r\n";}
            $this->set_data_to_sql($this->settings['shows_newest'], $this->newest_files);
            #$downloaded_ = $this->get_data_from_sql($this->settings['downloaded_nzbs']); # arrays/downloaded_nzbs.txt gets the prev downloaded files to recover
            
            #var_dump($downloaded_);
            if(!@$downloaded_)
            {
                if($this->verbose){echo "{1} Running download checker...\r\n";}
                $this->log_write("Empty Fetched Downloaded array - Running download checker...","audit");
                $this->download_new();
            }else
            {
                if($this->verbose){echo "Old Downloads not moved yet...\r\n";}
                $this->log_write("Fetched Downloaded array - Old Downloads not moved yet...","audit");
                $this->__set('downloaded', array_merge(array(), $downloaded_));
                #Run the cleanup
                $this->clean_up();
                #run download checker
                if($this->verbose){echo "{2} Running download checker...\r\n";}
                $this->log_write("Empty Fetched Downloaded array - Running download checker...","audit");
                $this->download_new();
                $this->recover = 0;
            }

            $this->log_write("Running download wait and cleaner...","audit");
            $this->download_wait_and_clean();

            if($this->run_once){$this->log_write("Run once complete","audit");die("Run Once Complete\r\n");}

            if($this->verbose){echo "Sleeping for ".($this->settings['scan_int']/60)." Min\r\n";}
            ### For some reason the dn_flag is not getting set, when a download is made.... XXX
            if(!$this->recover){$this->log_write("Dreaming Sequence initiated","audit");sleep($this->settings['scan_int']);}
        }
    }
    function clean_up()
    {
        foreach($this->downloaded as $key=>$dn)
        {
            if($this->verbose){echo "-------------------------\r\nCopy Downloaded to Home: ".$dn."\r\n";}
            if(file_exists($this->settings['done_dir'].$dn."/"))
            {
                $showdone_ = $this->settings['done_dir'].$dn."/";
                $get = $this->get_file($showdone_);
                if($get[0])
                {
                    if($this->copy_src_dest($dn, $get[1]))
                    {
                        if($this->verbose){echo "1\r\n";}
                        $this->coped[] = $this->downloaded[$key];
                        unset($this->downloaded[$key]);
                    }else
                    {
                        if($this->verbose){echo "0\r\n";}
                        $this->failed_copy[] = $this->downloaded[$key];
                        unset($this->downloaded[$key]);
                    }
                }else
                {
                    if($this->verbose){echo "/** NO MEDIA FILE FOUND :( **/\r\n";}
                }
            }else
            {
                if($this->verbose){echo "/**\r\n**  ERROR Trying to find a folder that should be there but isnt.\r\n**/\r\n";}
            }
            if($this->verbose){echo "-------------------------\r\n";}
        }
        $this->downloaded = array_merge(array(), $this->downloaded);
        $this->set_data_to_sql($this->settings['downloaded_nzbs'], $this->downloaded);
        if(@$this->failed_copy[0])
        {
            print_r($this->failed_copy);
            $this->set_data_to_sql($this->settings['failed_copy_file'], $this->failed_copy);

        }
	sleep(5);
        if(count($this->coped) != 0)
        {
            foreach($this->coped as $p)
            {
                $src = $this->settings['done_dir'].$p.'/';
                var_dump(system("$this->rm_cmd $src", $return));
		#if(!rrmdir($src))
                #{
                #    file_put_contents($this->settings['file_copy_log'], time()." ".$src, FILE_APPEND);
                #}else
                #{
                #    if($this->verbose){echo "Deleteing no longer needed folder $p.\r\n";}
                #}
            }
        }else
        {
            if($this->verbose){echo "No files copied, thats not good...";}
        }
    }
    function checks()
    {

        if(@$this->args['gen_playlist']===true)
        {
            echo "tentacle $this->ver\r\n======================================\r\n||       Just The Playlist...       ||\r\n======================================\r\n";
            $this->gen_shows_array();
            $this->generate_playlist_array($this->shows_array);
            $this->generate_playlist($this->playlist_array);
            die("Done...\r\n");
        }

        if(@$this->args['h']===true||@$this->args['help']===true)
        {
            die("
        tentacle $this->ver
        By: Longbow486
        Last Edit: $this->last_edit

        Description: $this->desc

        Arguments:

            -c, --config        The location of the settings file (default is settings/shows.txt)
            --run_once          Self explanitory, will run once and quit.
	    -q, --sqlhost	The MySQL host IP/Hostname that you want to use.
	    -y, --sqluser	The MySQL user That you want to use. If this is set, you will be
				    prompted for the password, so I would use the config file to define the user.
	    -g, --db		The MySQL Database name.
            -n, --nzb-sleep	The amount of time between each NZBMatrix search.
	    -s, --skipto	Tells tentacle to skip all shows but this one (really for dev purposes).
	    -v, --verbose       Tell me everything.
	    --gen_paylist       This will tell tentacle to only scan the media folder and generate a playlist file.
            --shows_dir         Overrides the Settings file value for the shows folder location.
            --dn_nzb_tmp        Overrides the NZB Temp folder location.
            --dn_dir            Overrides the SABNZBd autodownload folder locaton.
            --done_dir          Overrides the SABNZBd finished download folder location.
            --failed_copy_file  Overrides the Failed to copy files log location.
            --downloaded_nzbs   Overrides the Downloaded NZB files log location. Will be used for recovery if tentacle crashes.
            --shows_playlist    Overrides the Output playlist location.
            -l, --license	Show the license for tentacle and then exit.
            -h, --help          This text here dummy, how else did you get it?\r\n");
        }
	if(@$this->args['license']===true||@$this->args['l']===true)
        {
            die("
        tentacle $this->ver
        By: Longbow486
        Last Edit: $this->last_edit

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.\r\n");
        }
    }
    function check_last_scan_date()
    {
        if((time() - @$this->settings['last_scan']) > $this->settings['scan_int'])
        {return 1;}else{return 0;}
    }
    function check_nzb_error($string)
    {
        switch($string)
        {
            case "error:invalid_login":
                return "There is a problem with the username you have provided.";
            break;
            case "error:invalid_api":
                return "There is a problem with the API Key you have provided.";
            break;
            case "error:invalid_nzbid":
                return "There is a problem with the NZBid supplied.";
            break;
            case "error:vip_only":
                return "You need to be VIP or higher to access.";
            break;
            case "error:disabled_account":
                return "User Account Disabled.";
            break;
            case "error:no_nzb_found":
                return "No NZB found.";
            break;
            case "error:nothing_found":
                return 0;
            break;
            case "error:API_RATE_LIMIT_REACHED":
                return "Max Requests Reached";
            break;
            case "error:no_search":
                return "No Search Query";
            break;
            default:
                preg_match('/(?P<seconds>error:please_wait_\d+)/', $string, $seconds);
                if(!@is_null($seconds['seconds']))
                {return "Please wait ".$seconds['seconds']." Seconds.";}
                elseif(@is_null($string))
                {return "NO DATA RETURNED! :@";}
                else{return 0;}
            break;
        }
    }
    function check_for_skip($file)
    {
        $file_exp = explode(".", $file);
        $fcount = count($file_exp);
        switch(strtolower($file_exp[$fcount-1]))
        {
            case "":
                return 1;
            break;
            case "tbn":
                return 1;
            break;
            case "db":
                return 1;
            break;
            case "jpg":
                return 1;
            break;
            case "png":
                return 1;
            break;
            case "gif":
                return 1;
            break;
            case "dat":
                return 1;
            break;
            case "txt":
                return 1;
            break;
            case "ds_store":
                return 1;
            break;
            case "nfo":
                return 1;
            break;
            case "htm":
                return 1;
            break;
            case "html":
                return 1;
            break;
            case "torrent":
                return 1;
            break;
            case "diz":
                return 1;
            break;
            case "lnk":
                return 1;
            break;
            case "sfv":
                return 1;
            break;
            case "zip":
                return 1;
            break;
            case "par2":
                return 1;
            break;
            case "srr":
                return 1;
            break;
            case "srt":
                return 1;
            break;
            case "rtf":
                return 1;
            break;
            case "nzb":
                return 1;
            break;
            case "vlc media player_files":
                return 1;
            break;
            case "vlc media player":
                return 1;
            break;
            default:
                return 0;
            break;
        }
    }
    function check_shows_array()
    {
        $shows_list_tmp = $this->get_data_from_sql($this->settings['shows_file']);
        if(!$shows_list_tmp)
        {
            if($this->verbose){echo "No Shows array, running scan...\r\n";}
            $this->log_write("No Shows File, running scan...","audit");
            $this->gen_shows_array();
        }else
        {
            if($this->check_last_scan_date())
            {
                if($this->verbose){echo "Last scan was way long ago...\r\n";}
                $this->log_write("Last scan was way long ago...","audit");
                $this->gen_shows_array();
            }elseif($this->settings['dn_flag'])
            {
                if($this->verbose){echo "There were new shows downloaded, running scan...\r\n";}
                $this->log_write("There were new shows downloaded, running scan...","audit");
                $this->gen_shows_array();
            }else
            {
                if($this->verbose)
                {
                    $this->__set('shows_array', $shows_list_tmp);
                    echo "Scan was recent with no downloads: ".$this->settings['shows_file']."\r\nTotal Elements: ".count($shows_array, COUNT_RECURSIVE)."\r\n";
                    $this->log_write("Scan was recent with no downloads: ".$this->settings['shows_file']."\r\nTotal Elements: ".count($shows_array, COUNT_RECURSIVE),"audit");
                }
            }
        }
    }
    function copy_src_dest($dn, $get)
    {

        $show_exp = explode("+", $dn);
        $c = count($show_exp)-1;
        $data = $show_exp[$c];

        if($c > 1)
        {
            unset($show_exp[$c]);
            $show_name = implode(" ", $show_exp);
        }else
        {
            unset($show_exp[1]);
            $show_name = $show_exp[0];
        }
        preg_match('/(S(?P<S>\d+)E(?P<E>\d+))/',$data,$match);

        $season = "Season ".$match['S'];

        $dest_folder = $this->settings['shows_dir'].$show_name."/".$season."/";
        $dest = $dest_folder.$get;
        $src = $this->settings['done_dir'].$dn.'/'.$get;
        if($this->verbose){echo "FOUND MEDIA FILE: \r\n\t".$src."\r\n\r\n";}
        if(!file_exists($dest_folder))
        {
            if($this->verbose){echo "Folder didnt exist,\r\nCreated: $dest_folder\r\n";}
            mkdir($dest_folder);
        }
        if(!file_exists($dest))
        {
            if(copy($src, $dest))
            {
                if($this->verbose){echo "AND COPIED TO:\r\n\t$dest\r\n\r\n";}
		$this->log_write(time()." ".$dest, 'copy_log');
                unlink($src);
                return 1;
            }else
            {
                if($this->verbose){echo "FAILED TO COPY to:\r\n\t$dest\r\n\r\n";}
                $this->log_write(time()." ".$dest, 'failed_copy_log');
		return 0;
            }
        }
        else
        {
            if($this->verbose){echo "File exists, no need to copy.\r\n";}
	    $this->log_write(time()." Double not copied: ".$dest, $this->settings['copy_log']);
            unlink($src);
            return 1;
        }
    }
    function download_new()
    {
        $NZB_SEARCH_URL = "http://api.nzbmatrix.com/v1.1/search.php?search=";
        $NZB_KEY_URL = "&catid=41&sort=9&type=asc&username=".$this->settings['NZB_USER']."&apikey=".$this->settings['NZB_API_KEY'];
        $NZB_DL_URL = "http://nzbmatrix.com/api-nzb-download.php?id=";
        if(!is_array($this->newest_files)){return 0;}
        foreach($this->newest_files as $key=>$newest)
        {
	    if($this->skipto != "")if($key != $this->skipto){continue;}
	    if($key == ""){continue;}
            if($key == 'Penn & Teller - Bullshit!'){$key = 'Penn and Teller Bullshit!';}
            $new = $newest['newest'];
            if($this->verbose){echo "\r\n----------------------\r\nRAW ARRAY: ".$new."\r\n";}
            preg_match('/(?P<code>\w\d\d\w\d\d)/', $new, $matches);
            if(!@is_null($matches['code']))
            {
                $new_e = str_split(strtoupper($matches['code']), 3);
        #	var_dump($new_e);

                $season = $new_e[0][1].$new_e[0][2];
                $season = $season+0;
                $episode = $new_e[1][1].$new_e[1][2];
                $episode = $episode+0;

                if($this->verbose){echo "Show: $key\r\nNewest:\r\n\tSeason: ".$season."\r\n\tEpisode: $episode\r\n";}

                $nexts = $season+1;

                $nexte = $episode+1;
                for($I=$nexte; $I<30; $I++)
                {
                    $first_check = "S".str_pad($season, 2, 0, STR_PAD_LEFT)."E".str_pad($I, 2, 0, STR_PAD_LEFT);
                    $term = urlencode($key." ".$first_check);
                    $this->term = $term;
		    sleep($this->nzb_sleep);

                    if($this->verbose){echo "----------\r\nTERM1: ".$term."\r\n----------\r\n";}
                    $SearchURL = $NZB_SEARCH_URL.$term.$NZB_KEY_URL;
            #	echo $SearchURL."\r\n";
                    $NZBSearchResult = @file($SearchURL);
                    $check_nzb_error_ret = $this->check_nzb_error($NZBSearchResult[0]);
                    if($check_nzb_error_ret !== 0){die("\r\n/**\r\n*  CRITICAL ERROR\r\n*  $check_nzb_error_ret (".@date('d M Y H:i:s').")\r\n**/\r\n");}

                    if($this->verbose){echo $NZBSearchResult[0]."\r\n";}

                    if($NZBSearchResult[0] == "error:nothing_found")
                    {
                        if($this->verbose){echo "Nothing Found\r\n";}
                        for($neps = 1; $neps<30; $neps++)
                        {
                            $check = "S".str_pad($nexts, 2, 0, STR_PAD_LEFT)."E".str_pad($neps, 2, 0, STR_PAD_LEFT);
                            $term = urlencode($key." ".$check);
                            sleep(12);
                            if($this->verbose){echo "----------\r\nTERM2: ".$term."\r\n----------\r\n";}
                            $SearchURL = $NZB_SEARCH_URL.$term.$NZB_KEY_URL;
            #		echo $SearchURL."\r\n";
                            $NZBSearchResult = file($SearchURL);
                            $check_nzb_error_ret = $this->check_nzb_error($NZBSearchResult[0]);
                            if($check_nzb_error_ret !== 0){die("\r\n/**\r\n*  CRITICAL ERROR\r\n*  $check_nzb_error_ret (".@date('d M Y H:i:s').")\r\n**/\r\n");}
                            if($NZBSearchResult[0] != "error:nothing_found")
                            {
                                $this->downloaded[] = $term;
                                for($III = 0; $III < count($NZBSearchResult);$III++)
                                {
                                    preg_match('/(?P<id>:\d+)/', $NZBSearchResult[$III], $id);
                                    $id = str_replace(":", "", $id['id']);

                                    if($this->verbose){echo "\tNZB MATRIX ID: $id\r\n";
                                    echo "\tNZB MATRIX NAME: ".str_replace("NZBNAME:","",$NZBSearchResult[$III+1])."\r\n";}

                                    $DL_URL = $NZB_DL_URL.$id.$NZB_KEY_URL;
                                    $NZB_FILE = file($DL_URL);
                                    $NZB_IMP = implode("\r\n", $NZB_FILE);

                                    if($this->verbose){echo "Temp File: ".$this->settings['dn_nzb_tmp'].$term.".nzb\r\n"
				    ."Auto Download File: ".$this->settings['dn_dir'].$term.".nzb\r\n";}
				    if(file_put_contents($this->settings['dn_nzb_tmp'].$term.".nzb", $NZB_IMP))
				    {
					set_data_to_sql($this->settings['faild_copy_log'], $this->settings['dn_nzb_tmp'].$term.".nzb");
				    }else
				    {
					set_data_to_sql($this->settings['copy_log'], $this->settings['dn_nzb_tmp'].$term.".nzb");
				    }
                                    if(file_put_contents($this->settings['dn_dir'].$term.".nzb", $NZB_IMP))
				    {
					set_data_to_sql($this->settings['faild_copy_log'], $this->settings['dn_dir'].$term.".nzb");
				    }else
				    {
					set_data_to_sql($this->settings['copy_log'], $this->settings['dn_dir'].$term.".nzb");
				    }
                                    $this->settings['dn_flag'] = 1;
				    break;
                                }
                            }else
                            {
                                if($this->verbose){echo "Nothing Found - Skipping this show.\r\n";}
                                break 2;
                            }
                        }
                    }else
                    {
                        $this->downloaded[] = $term;
			# Really need to change this, right now I just take the first returned result
			# from NZBMatrix. This may not always be what we are looking for. XXX
			$nzb_res = $this->nzb_search($NZBSearchResult);
                    }
                    if($this->verbose){echo "\r\n";}
                }
            }
        }
	if($this->conn->query("UPDATE  `tentacle`.`settings` SET  `dn_flag` =  '".$this->settings['dn_flag']."' WHERE  `settings`.`id` = 1 LIMIT 1"))
	return 1;
    }
    function nzb_search($NZBSearchResult)
    {
	$term = $this->term;
	for($II = 0; $II < count($NZBSearchResult);$II++)
	{
	    preg_match('/(?P<id>:\d+)/', $NZBSearchResult[$II], $id);
	    $id = str_replace(":", "", $id['id']);
	    if($this->verbose){echo "\tNZB MATRIX ID: $id\r\n\tNZB MATRIX NAME: ".str_replace("NZBNAME:","",$NZBSearchResult[$II+1])."\r\n";}
	    $DL_URL = $NZB_DL_URL.$id.$NZB_KEY_URL;
	    if(!$NZB_FILE = @file($DL_URL))
	    {
		if($this->verbose){echo "\\****** FAILED TO FETCH HTTP DATA FROM NZBMATRIX\r\n";}
		$this->log_write("Failed to grab data from NZBmatrix, http request failed...", 'error');
		break;
	    }
	    $NZB_IMP = implode("\r\n", $NZB_FILE);
	    if($this->verbose){echo "Temp File: ".$this->settings['dn_nzb_tmp'].$term.".nzb\r\n"
	    ."Auto Download File: ".$this->settings['dn_dir'].$term.".nzb\r\n";}
	    if(file_put_contents($this->settings['dn_nzb_tmp'].$term.".nzb", $NZB_IMP))
	    {
		file_put_contents($this->settings['faild_copy_log'], time()." ".$this->settings['dn_nzb_tmp'].$term.".nzb", FILE_APPEND);
	    }else
	    {
		file_put_contents($this->settings['copy_log'], time()." ".$this->settings['dn_nzb_tmp'].$term.".nzb", FILE_APPEND);
	    }

	    if(file_put_contents($this->settings['dn_dir'].$term.".nzb", $NZB_IMP))
	    {
		file_put_contents($this->settings['faild_copy_log'], time()." ".$this->settings['dn_dir'].$term.".nzb", FILE_APPEND);
	    }else
	    {
		file_put_contents($this->settings['copy_log'], time()." ".$this->settings['dn_dir'].$term.".nzb", FILE_APPEND);
	    }
	    $this->settings['dn_flag'] = 1;
	    break;
	}
    }
    function download_wait_and_clean()
    {
	var_dump($this->settings['dn_flag']);
	var_dump($this->downloaded);
        if(@$this->downloaded[0] == "")
        {
            if($this->verbose){echo "No new Shows NZBs downloaded...\r\n";}
            $this->settings['dn_flag'] = 0;
	    $this->set_data_to_sql($this->settings['downloaded_nzbs'], $this->downloaded);
        }else
        {
            #$this->settings['dn_flag'] = 1;
            $this->set_data_to_sql($this->settings['downloaded_nzbs'], $this->downloaded);

	    #if the previous files have not been moved, do so
            if($this->recover)
            {
                if($this->verbose){echo "Recover Downloaded NZB's:\r\n";}
                foreach($this->downloaded as $dn)
                {
                    $source = $this->settings['dn_dir'].$dn.".nzb";
                    $dest = $this->settings['dn_dir'].$dn.".nzb";
                    if(copy($source, $dest))
                    {
                        if($this->verbose){echo "Copy NZB: ".$source."\r\nTo: ".$dest."\r\n----------------\r\n\r\n";}
                    }else
                    {
                        if($this->verbose){echo "FAILED Copy NZB: ".$source."\r\nTo: ".$dest."\r\n----------------\r\n\r\n";}
                    }
                }
                #wait.
                $SAB_refresh = (count($this->downloaded)*10);
                if($this->verbose){echo "Sleep for (n{NZBs}*10)sec to let SABnzbd gather all the files and start downloading.\r\n".$SAB_refresh."\r\n";}
                sleep($SAB_refresh);
            }


            $SAB_Status = $this->SAB_Status('state');
            echo $SAB_Status."\r\n";
            $sl=0;
            while($SAB_Status != "IDLE")
            {
                if($sl>5)
                {
                    if($this->verbose){echo "Sleeping for a little while, SABnzbd still not done downloading.\r\n";}
                    $sl=0;
                }
                else{echo ".";}
                sleep(30);
                $sl++;
                $SAB_Status = $this->SAB_Status('state');
    #	echo $SAB_Status."\r\n";
            }
            #var_dump($this->downloaded);
            if($this->verbose){echo "\r\nLooks like SABnzbd has finished downloading.\r\n";}
            $check_folders = $this->SAB_check_folders();
            $sl=0;
            $dc = count($this->downloaded);
            while($check_folders[0] != $dc)
            {
        #	print_r($check_folders);
                if($sl>5)
                {
                    if($this->verbose){echo "Some folders are missing, SABnzbd is either repairing or extracting the file.\r\n";}
                    $sl=0;
                }
                else{echo ".";}
                sleep(30);
                $sl++;
                $check_folders = $this->SAB_check_folders();
            }

            if(@is_array($check_folders['failed']))
            {
                $failed = array_merge(array(), $check_folders['failed']);
                $this->set_data_to_sql($this->settings['failed_file'], $failed);
            }
            $this->clean_up();
        }
	return 1;
    }
    function find_type($file)
    {
        $file_exp = explode(".", $file);
        $fcount = count($file_exp);
        if(strtolower($file_exp[$fcount-1]) == ""){echo $file."\r\n";}
        return strtolower($file_exp[$fcount-1]);
    }
    function get_file($dir)
    {
        $i=0;
        $ret = array($i);
        if($dh = opendir($dir))
        {
            while (($file = readdir($dh)) !== false)
            {
		if($file == "."){continue;}
		if($file == ".."){continue;}
		if(is_dir($dir.'/'.$file))
		{
		    $ret_ = $this->get_file($dir.'/'.$file);
		    if($ret_[0]!=0)
		    {
			$ret[0]=1;
			$ret[1]=$dir.'/'.$ret_[1];
			break;
		    }
		}
                if($this->check_for_skip($file)){continue;}
                $ret[0]=1;
                $ret[1]=$file;
            }
        }
        return $ret;
    }
    function get_newest_files($array, $level = 0)
    {
        $ret = array();
        if($level != 0)
        {
            $keys = array_keys($array);
            $max = count($keys);
            if($max == 0)
            {
                return;
            }
            $key = $keys[$max-1];

            if(@is_array($array[$key]))
            {
                $level++;
                $ret = $this->get_newest_files($array[$key], $level);
                $level--;
            }else
            {
                $ret = $array[$key];
            }
        }else
        {
            foreach($array as $key=>$a)
            {
                if(!@$a['dead'])
                {
                    $level++;
                    $ret[$key]['newest'] = $this->get_newest_files($a, $level);
                    $level--;
                }
            }
        }
        return $ret;
    }
    function gen_shows_array()
    {
        if($this->verbose){echo "\tGenerating Shows Array RAW:\r\n";}
        $this->recurs_dir($this->settings['shows_dir']);

        if($this->verbose){echo "Writing Shows Array to Table: ".$this->settings['shows_file']."\r\n";}
        $this->set_data_to_sql($this->settings['shows_file'], $this->shows_array);

        if($this->verbose){echo "Total Elements: ".count($this->shows_array, COUNT_RECURSIVE)."\r\n";}
        $this->settings['last_scan'] = time();

        /*
         * XXX CHANGE THIS TO JUST UPDATE THE TIME STAMP FOR LAST SCAN
         */
        $this->update_time();

        $this->__set('shows_array', $this->shows_array);
	if($this->conn->query("UPDATE  `tentacle`.`settings` SET  `last_scan` =  '".$this->settings['last_scan']."' WHERE  `settings`.`id` = 1 LIMIT 1"))
	return 1;
    }
    function get_file_types($array)
    {
        $out = array();
        foreach($array as $key=>$val)
        {
            if(is_array($val))
            {
                $ret_array = $this->get_file_types($val);
                $out[$key] = $ret_array;
            }else
            {
                $ext = $this->find_type($val);
                if(@is_null($out[$ext]))
                {
                    $out[$ext] = 1;
                }else
                {
                    $out[$ext]++;
                }
            }
        }
        return $out;
    }
    function get_type_count($type_array)
    {
        foreach($type_array as $key=>$val)
        {
            if($val==""){continue;}
            if(is_array($val))
            {
                foreach($val as $key1=>$val1)
                {
                    if($val1==""){continue;}
                    if(!is_array($val1))
                    {
                        if(@is_null($typea[$key1]))
                        {
                            $typea[$key1] = $val1;
                        }else
                        {
                            $typea[$key1] = $typea[$key1]+$val1;
                        }
                    }else
                    {

                        foreach($val1 as $key2=>$val2)
                        {
                            if($val2==""){continue;}
                            if(!is_array($val2))
                            {
                                if(@is_null($typea[$key2]))
                                {
                                    $typea[$key2] = $val2;
                                }else
                                {
                                    $typea[$key2] = $typea[$key2]+$val2;
                                }
                            }else
                            {
                                foreach($val2 as $key3=>$val3)
                                {
                                    if($val3==""){continue;}
                                    if(@is_null($typea[$key3]))
                                    {
                                        $typea[$key3] = $val3;
                                    }else
                                    {
                                        $typea[$key3] = $typea[$key3]+$val3;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
	$typea['total'] = 0;
	foreach($typea as $type)
	{
            $typea['total'] = $typea['total']+$type;
	}
	return $typea;
}
    function generate_playlist($array)
    {
        $data = "<asx version = \"3.0\" >\r\n";
        foreach($array as $a)
        {
            $exp = explode($this->sep, $a);
            $filename = $exp[count($exp)-1];
            if($filename == "its dead jim"){continue;}
            $data .= "\t<entry>\r\n\t\t<title>$filename</title>\r\n\t\t<ref href = \"$a\" />\r\n\t</entry>\r\n";
        }
        if($this->verbose){echo "PLAYLIST FILE: ".$this->settings['shows_playlist']."\r\n";}
        file_put_contents($this->settings['shows_playlist'], $data."</asx>");
	return 1;
    }
    function generate_playlist_array($array, $Fkey="", $level=0)
    {
        $ret = array();
        if($Fkey == "")
        {
	    $Fkey = $this->settings['shows_dir'];
        }
        foreach($array as $key=>$a)
        {
	    if($key == "dead" && $key !== FALSE){continue;}
	    if(!is_int($key) && $Fkey != "")
	    {
		$key_ = $Fkey.$key.$this->sep;
	    }else
	    {
		$key_ = $Fkey;
	    }
	    if(is_array($a))
	    {
		$level++;
		$this->generate_playlist_array($a, $key_, $level);
		$ret = array_merge($ret, $this->playlist_array);
		$level--;
	    }else
	    {
		$ret[] = $key_.$a;
	    }
        }
        $this->__set('playlist_array', $ret);
	return 1;
    }
    function pars_args($argv)
    {
        array_shift($argv);
        $out = array();
        foreach ($argv as $arg){
            if (substr($arg,0,2) == '--'){
                $eqPos = strpos($arg,'=');
                if ($eqPos === false){
                    $key = substr($arg,2);
                    $out[$key] = isset($out[$key]) ? $out[$key] : true;
                } else {
                    $key = substr($arg,2,$eqPos-2);
                    $out[$key] = substr($arg,$eqPos+1);
                }
            } else if (substr($arg,0,1) == '-'){
                if (substr($arg,2,1) == '='){
                    $key = substr($arg,1,1);
                    $out[$key] = substr($arg,3);
                } else {
                    $chars = str_split(substr($arg,1));
                    foreach ($chars as $char){
                        $key = $char;
                        $out[$key] = isset($out[$key]) ? $out[$key] : true;
                    }
                }
            } else {
                $out[] = $arg;
            }
        }
        $this->__set('args', $out);
	return 1;
    }
    function recurs_dir($dir, $level = 0)
    {
        $tabs = "";
        $level_t = $level;
        $array = array();
        if(is_dir($dir))
        {
            if($dh = opendir($dir))
            {
                $r = 0;
                while (($file = readdir($dh)) !== false)
                {
                    if($this->verbose)
                    {
                        if($this->verbose)
                        {
                            if($r===0){echo "|\r";}
                            if($r===10){echo "/\r";}
                            if($r===20){echo "-\r";}
                            if($r===30){echo "|\r";}
                            if($r===40){echo "/\r";}
                            if($r===50){echo "-\r";}
                            if($r===60){echo "\\\r";$r=0;}
                            $r++;
                        }
                    }

                    while($level_t > 0)
                    {
                        $tabs .= "\t";
                        $level_t--;
                    }
                    if($file != "dead.txt")
                    {
                        if($this->check_for_skip($file))
                        {
                            continue;
                        }
                    }

                    if(is_dir($dir.$file))
                    {
                        $array[$file] = array();
                        $level++;
                        $this->recurs_dir($dir.$file."/", $level);
                        $level--;
                        $array[$file] = $this->shows_array;
                    }else
                    {
                        if($file != "dead.txt")
                        {
                            $array[] = $file;
                        }
                        else
                        {
                            $array['dead'] = "its dead jim";
                        }
                    }
                }
                if($this->verbose){echo "\r";}
                $this->__set('shows_array', array_merge(array(),$array));
                #var_dump($this->shows_array);
            }
        }
    }
    function run_file_type_stats()
    {
        if(@$this->settings['run_stats'] == true)
        {
            if($this->verbose){echo "Compiling Media Types:\r\n";}
            $this->shows_details = $this->get_file_types($this->shows_array);
            $this->types = $this->get_type_count($this->shows_details);

            if($this->verbose){echo "Statistics:\r\n";}
            print_r($this->types);
            $this->set_data_to_sql($this->settings['shows_details'], $this->shows_details);
	    return 1;
        }else
        {
            if($this->verbose){echo "Not running File type stats...\r\n";}
	    return 0;
        }
    }
    function SAB_check_folders()
    {
        $ret[0] = 0;

        foreach($this->downloaded as $dn)
        {
            if(file_exists($this->settings['done_dir'].$dn."/"))
            {
                $ret[0]++;
                $ret['passed'][] = $dn;
                $this->log_write("SAB Folder Passed: ".$dn, 'audit');
            }elseif(file_exists($this->settings['done_dir'].$this->settings['FAILED'].$dn."/"))
            {
                $ret[0]++;
                $ret['failed'][] = $dn;
                $this->log_write("SAB Folder Failed: ".$dn, 'failure');
            }
        }
        return $ret;
    }
    function SAB_Status($element)
    {
        $SAB_url_path = "http://".$this->settings['SAB_Host'].":".$this->settings['SAB_Port']."/api?mode=qstatus&output=xml&apikey=".$this->settings['SAB_API_KEY'];
        $SAB_Status = @xml2ary(@implode("", @file($SAB_url_path)));
        switch($element)
        {
            case "state":
                return $SAB_Status['queue']['_c']['state']['_v'];
            break;
            case "have_warnings":
                return $SAB_Status['queue']['_c']['have_warnings']['_v'];
            break;
            case "timeleft":
                return $SAB_Status['queue']['_c']['timeleft']['_v'];
            break;
            case "mb":
                return $SAB_Status['queue']['_c']['mb']['_v'];
            break;
            case "noofslots":
                return $SAB_Status['queue']['_c']['noofslots']['_v'];
            break;
            case "paused":
                return $SAB_Status['queue']['_c']['paused']['_v'];
            break;
            case "paused_int":
                return $SAB_Status['queue']['_c']['paused_int']['_v'];
            break;
            case "loadavg":
                return $SAB_Status['queue']['_c']['loadavg']['_v'];
            break;
            case "mbleft":
                return $SAB_Status['queue']['_c']['mbleft']['_v'];
            break;
            case "diskspace1":
                return $SAB_Status['queue']['_c']['diskspace1']['_v'];
            break;
            case "diskspace2":
                return $SAB_Status['queue']['_c']['diskspace2']['_v'];
            break;
            case "kbpersec":
                return $SAB_Status['queue']['_c']['kbpersec']['_v'];
            break;
            case "jobs":
                return $SAB_Status['queue']['_c']['jobs']['job']['timeleft']['_v'];
            break;
            case "jobs":
                return $SAB_Status['queue']['_c']['jobs']['_v'];
            break;
            case "speed":
                return $SAB_Status['queue']['_c']['speed']['_v'];
            break;
        }
    }
    function GetSQLSettings()
    {
	#$this->conn = new mysqli($this->settings['sqlhost'], $this->settings['sqluser'], $this->settings['sqlpwd'], $this->settings['db']);
	$this->conn = new PDO($this->settings['sqlhosttype'].':dbname='.$this->settings['db'].';host='.$this->settings['sqlhost'], $this->settings['sqlpwd'], $this->settings['sqluser']);
	if(mysqli_connect_errno())
	{
	    if($this->verbose)
	    {
		printf("Connect failed: %s\n", mysqli_connect_error());
		$this->log_write("Connect failed: ".mysqli_connect_error(), 'failure');
	    }
	    exit();
	}
	$result = $this->conn->query("SELECT * FROM `settings` where `id`='1'", 1);
        $settings = $result->fetch_array(1);
        $this->log_write("Grabbed MySQL based settings...","audit");
        #var_dump($this->settings);
        $this->__set('settings', array_merge($this->settings, $settings));
        #var_dump($this->settings);
	$this->log_write("Connected to MySQL Host: ".$this->settings['sqlhost'], 'audit');
    }
    function log_write($mesg, $dest)
    {
        #$mesg = htmlspecialchars($mesg);
	$prep = $this->conn->prepare("INSERT INTO `history` (`id` ,`time_stamp` ,`mesg` ,`catagory`) VALUES (NULL , '?', '?', '?')", array(PDO::ATTR_CURSOR => PDO::CURSOR_FWDONLY));
        if($prep->execute( array( date('Y-m-d H:i:s'), $this->conn->quote($mesg), $this->conn->quote($dest) ) ) )
        {
            if($this->verbose){echo "Logged message to SQL\r\n";}
        }
    }
    function update_time()
    {
        if(!$this->conn->query("UPDATE `settings` SET  `last_scan` =  '".time()."' WHERE `id` = 1"))
        {
	    $error = $this->conn->errorInfo();
            if($this->verbose){echo "Failed to Log data to `$table` (".time().")\r\n".$error[2];}
        }else
        {
            if($this->verbose){echo "Logged data to `$table` (".time().")\r\n";}
        }
    }
    function set_data_to_sql($table,$array)
    {
        $data = $this->conn->quote(serialize($array));
       # var_dump($data);

        if(!$this->conn->query("INSERT INTO `$table` (`id` ,`data` ,`time`) VALUES (NULL ,  '$data',  '".time()."')"))
        {
	    $error = $this->conn->errorInfo();
            if($this->verbose){echo "Failed to Log data to `$table` (".time().")\r\n".$error[2];}
        }else
        {
            if($this->verbose){echo "Logged data to `$table` (".time().")\r\n";}
        }
    }
    function get_data_from_sql($table)
    {
	$result = $this->conn->query("SELECT * FROM `$table` ORDER BY `id` DESC LIMIT 1", 1);
        if(!empty($result))
        {
	    $error = $this->conn->errorInfo();
	    if($this->verbose){echo "Failed to Fetch data from `$table` (".time().")\r\n".$error[2];}
        }else
        {
            if($this->verbose){echo "Fetched data from `$table` (".time().")\r\n";}
            return unserialize($result[0]['data']);
        }
    }
}




#############################
###### Other Functions ######
#############################

function _del_p(&$ary)
{
    foreach ($ary as $k=>$v) {
        if ($k==='_p') unset($ary[$k]);
        elseif (is_array($ary[$k])) _del_p($ary[$k]);
    }
}
/**
 * Checks if an array contains no arrays
 * @param  arary $array : The array to be checked
 * @return boolean      : true if $array contains no sub arrays
 *                        false if it does
 */
function has_no_sub_arrays($array)
{
   if (!is_array($array)) {
      return true;
   }
   foreach ($array as $sub) {
      if (is_array($sub)) {
         return false;
      }
   }
   return true;
}
function rrmdir($dir)
{
    if (is_dir($dir))
    {
	if ($dh = opendir($dir))
	{
	    $objects=array();
	    while (($file = readdir($dh)) !== false)
	    {
		$objects[] = $file;
	    }
	    closedir($dh);
	}
        foreach ($objects as $object)
        {
            if ($object != "." && $object != "..")
            {
                if(is_dir($dir."/".$object))
                {
                    if(rrmdir($dir."/".$object)){return 1;}
		    else{
			if(!rmdir($dir.'/'.$object)){ECHO "Failed to delete: $dir/$object";return 0;}
			else{return 1;}
		    }
                }else{
                    if(unlink($dir."/".$object)){return 1;}
		    else{ECHO "Failed to delete: $dir/$object";return 0;}
                }
            }
            reset($objects);
        }
        if(rmdir($dir)){return 1;}
	else{return 0;}
    }
}
/**
 * Adds quotes to $val if its not an integer
 * @param mixed $val : the value to be tested
 */
function quote($val)
{
   return is_int($val)?$val:"\"".$val."\"";
}
function xml2ary(&$string)
{
    $parser = xml_parser_create();
    xml_parser_set_option($parser, XML_OPTION_CASE_FOLDING, 0);
    xml_parse_into_struct($parser, $string, $vals, $index);
    xml_parser_free($parser);

    $mnary=array();
    $ary=&$mnary;
    foreach ($vals as $r)
    {
        $t=$r['tag'];
        if ($r['type']=='open')
        {
            if (isset($ary[$t]))
            {
                    if (isset($ary[$t][0]))
                    {
                            $ary[$t][]=array();
                    }
                    else
                    {
                            $ary[$t]=array($ary[$t], array());
                    }
                    $cv=&$ary[$t][count($ary[$t])-1];
            }else
            {
                    $cv=&$ary[$t];
            }
            if(isset($r['attributes']))
            {
                    foreach($r['attributes'] as $k=>$v)
                    {
                            $cv['_a'][$k]=$v;
                    }
            }
            $cv['_c']=array();
            $cv['_c']['_p']=&$ary;
            $ary=&$cv['_c'];
        }
        elseif($r['type']=='complete')
        {
            if(isset($ary[$t])) // same as open
            {
                    if(isset($ary[$t][0]))
                    {
                        $ary[$t][]=array();
                    }else
                    {
                        $ary[$t]=array($ary[$t], array());
                    }
                    $cv=&$ary[$t][count($ary[$t])-1];
            } else
            {
                $cv=&$ary[$t];
            }
            if(isset($r['attributes']))
            {
                foreach ($r['attributes'] as $k=>$v)
                {
                        $cv['_a'][$k]=$v;
                }
            }
            $cv['_v']=(isset($r['value']) ? $r['value'] : '');
        }elseif($r['type']=='close')
        {
            $ary=&$ary['_p'];
        }
    }
    _del_p($mnary);
    return $mnary;
}
function get_pwd()
{
    #ask for password
    fwrite(STDOUT, "tentacle MySQL User Password :# ");
    system('stty -echo');
    $pwd = trim(fgets(STDIN));
    system('stty -echo');
    return $pwd;
}
?>