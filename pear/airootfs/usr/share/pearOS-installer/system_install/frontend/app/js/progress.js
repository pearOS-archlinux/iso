/* 
* Copyright Alexandru Balan under The Pear Project
* This file is released under the Pear Public Liense 
* v2 and later
*
* This script shows the progress of installation
* and it is meant to be used as part of the
* pearOS system install application
* 
* By using this installer, you are aware of
* the fact that it will ERASE the selected
* disk and will replace the OS you have
* currently running, with pearOS, as there
* is no Dual-Boot support yet.
*
* There is a workaround if you want dual
* boot. You can install pearOS and then
* an os of your choice.
*
* Do not blame on me for that, it is the
* "hackintosh" way, I work to fix that
* soon.
*
* I hope that you will enjoy the pearOS
* experience :)
*
* Now, let's get to the code: 	*/

function print_disk() {
const fs = require("fs");
var disk="";
var prog="";

fs.readFile("/tmp" + "/disk-to-install", (error, data) => {
    if(error) {
        throw error;
    }
	var disk=`
	<li>
	<label class="label_for_disk">
	<input type="radio" id="disk" name="disk" value="` + data.toString() + `">
	<img class="disk_logo_progress" height=50px src="../../resources/disk.png"></img>
	<p id="label_disk" class="disk_title">` + data.toString() + `</p>
	</label>
	</li>
	`;

	setInterval(function() {
                fs.readFile("/tmp" + "/progress", (error, data) => {
	            if(error) {
		    throw error;
            	}

            if (data.toString() == "Installation finished") {
		var prog = '<p align="center" class="setup-text">Installation finished. You can close this window (can use ALT+F4) and reboot<br>your new pearintosh, or check the log located on the desktop.</p>'
		document.getElementById("disk_list").innerHTML = prog;
                } else {
                    var prog = `
                	<br><progress id="file" value="` + data.toString() + `" max="100"> 69% </progress>
                	`
			document.getElementById("disk_list").innerHTML = disk + prog;
                };
            });
        }, 1000);
	});
}

document.getElementById("close-btn").addEventListener("click", function (e) {
       var window = remote.getCurrentWindow();
       window.close();
  });
