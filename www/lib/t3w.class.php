<?php
#    t3w.class.php, Some shared functions for both the Client page and the admin page
#    Copyright (C) 2010
#
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
class t3w {
    public function  __construct() {
	require('config.inc.php');
        #setup the MySQL Connection
        $this->conn = new mysqli(SQL_HOST, SQL_USER, SQL_PWD, SQL_DB);
        
        #setup the Smarty object
	require(SMARTY_DIR.'Smarty.class.php');
	$this->smarty = new Smarty();
	$this->smarty->setTemplateDir( WWW_DIR.'smarty/templates/' );
	$this->smarty->setCompileDir( WWW_DIR.'smarty/templates_c/' );
	$this->smarty->setCacheDir( WWW_DIR.'smarty/cache/' );
	$this->smarty->setConfigDir( WWW_DIR.'/smarty/configs/' );
    }

    function grab_index()
    {
        ### Get tentacle Daemon Status
	list($pid) = @file(PID_FILE);
	exec("ps vp $pid", $output);
	$status_detail = $output[1];
	$img = "on.gif";
	if($status_detail=="")
	{
	    $status_detail = "tentacle is not running...";
	    $img = "off.gif";
	}

        $this->smarty->assign('status_img', $img);
	$this->smarty->assign('status_detail', $status_detail);
        $this->smarty->assign('status', $status);


	#### Grab Log History
	if($result = $this->conn->query("SELECT * FROM `history`",1))
	{
	    $history = array();
	    while($rows = $result->fetch_array(1))
	    {
		$history[] = $rows;
	    }
	    $this->smarty->assign('history', $history);
	    $this->smarty->display('index.tpl');
	}else
	{
	    echo $this->conn->error;
	}

    }

    function check_proc()
    {
	exec("ps ax | grep tentacle.php", $return);
	$this->smarty->assign('name', $return[0]);
	$this->smarty->display('procview.tpl');
    }

}

?>