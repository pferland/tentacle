<?php
#    index.php, Some shared functions for both the Client page and the admin page
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
require('lib/t3w.class.php');
$tw3 = new tentacle_http();

switch(htmlspecialchars($_GET["page"]))
{
    case "index":
	$tw3->grab_index();
	break;
    case "status":
	$tw3->check_proc();
	break;
}
?>