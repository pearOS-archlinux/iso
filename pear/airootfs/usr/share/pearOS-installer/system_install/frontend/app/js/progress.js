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

            var progressText = data.toString();
            
            // Verifică dacă instalarea a eșuat complet
            if (progressText.startsWith("INSTALLATION FAILED")) {
                var errorMessage = progressText.replace("INSTALLATION FAILED: ", "");
                var prog = '<p align="center" class="setup-text" style="color: #ff0000;">Installation Failed!</p>';
                prog += '<p align="center" class="setup-text" style="color: #ff6666;"><b>Error:</b> ' + errorMessage + '</p>';
                prog += '<p align="center" class="setup-text">Please check <b>/tmp/install.log</b> for details.<br>You may need to restart the installer or check your disk.</p>';
                document.getElementById("disk_list").innerHTML = prog;
            }
            // Verifică dacă instalarea s-a terminat (cu sau fără warnings)
            else if (progressText.startsWith("Installation finished")) {
                var prog = '';
                
                // Verifică dacă sunt warnings
                if (progressText.includes("warnings")) {
                    // Extrage numărul de warnings
                    var warningMatch = progressText.match(/(\d+) warnings/);
                    var warningCount = warningMatch ? warningMatch[1] : '0';
                    
                    prog = '<p align="center" class="setup-text" style="color: #ffaa00;">Installation finished with ' + warningCount + ' warnings.</p>';
                    prog += '<p align="center" class="setup-text">Some packages failed to install. You can close this window (ALT+F4) and reboot,<br>or check the logs: <b>/tmp/install.log</b> and <b>/tmp/failed_packages.log</b></p>';
                } else {
                    prog = '<p align="center" class="setup-text" style="color: #00ff00;">Installation finished successfully!</p>';
                    prog += '<p align="center" class="setup-text">You can close this window (can use ALT+F4) and reboot<br>your new pearintosh, or check the log located on the desktop.</p>';
                }
                
                document.getElementById("disk_list").innerHTML = prog;
            } else {
                // Afișează progress bar
                var prog = `
                	<br><progress id="file" value="` + progressText + `" max="100"> ` + progressText + `% </progress>
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
