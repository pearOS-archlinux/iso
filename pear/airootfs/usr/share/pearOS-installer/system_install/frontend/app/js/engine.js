function open_gparted() {
const { exec } = require('child_process');
exec('gparted', (err, stdout) => {
    console.log(`${stdout}`);
})
}

function open_browser() {
const { exec } = require('child_process');
exec('firefox', (err, stdout) => {
    console.log(`${stdout}`);
})
}

function open_packup() {
const { exec } = require('child_process');
exec('', (err, stdout) => {
    console.log(`${stdout}`);
})
}

function open_installer() {
 location.href = "page_install.html";
}
///////////////////////////////////////////////////////////////////////////////////////////////////

function list_disk() {
//vars:
const { exec } = require('child_process');
count = 0;
i = 1 ;
f = 0;
var z=``;
var diskname = "";
var disksize ="";

exec('list_disk count', (err, numberofdisks) => {
var sCount = `${numberofdisks}`
count = parseInt(sCount);
console.log("Available disks are:" + count);

while (i < (count+1)) {
        console.log("THE VALUE IS " + i);
        const currentIndex = i;
        
		exec("list_disk " + currentIndex, (err, diskPath) => {
			exec("list_disk name " + currentIndex, (err, diskName) => {
				var zi=`
				<li>
				  <label class="label_for_disk">
				    <input type="radio" id="disk${currentIndex}" name="disk" value="${diskPath.trim()}">
        	    		<img class="disk_logo" height=50px src="../../resources/disk.png"></img>
        	    		<p id="label_disk${currentIndex}" class="disk_title"><b>${diskName.trim()}</b></p>
        	    		<p class="disk_title" style="font-size: 0.8em; color: #999;">${diskPath.trim()}</p>
				  </label>
				</li>
				`;
				z += zi;
				document.getElementById("disk_list").innerHTML = z;
			});
        });
        i++;
	}
	})
}

function select_disk() {

if(! navigator.onLine){
	alert('You need an active internet connection to install pearOS NiceCC0re on your device. Please connect to the internet and try again.');
	window.location.href='';
	} else {
        var radios = document.getElementsByName('disk');
        for (var i = 0, length = radios.length; i < length; i++) {
          if (radios[i].checked) {
	  const fs = require('fs');
	  fs.writeFileSync('/tmp/disk-to-install', '' + radios[i].value);
	  // starting the shell //
	  const { exec } = require('child_process');
	  exec("sudo setup " + radios[i].value + "&> ~/Desktop/install.log", (err, stdout) => {
	  })
	// ending the shell //
	window.location.href='page_install_progress.html';
        break;
        }
    }
  }
}

var p = document.getElementsByTagName("p");

function print_disk(ctrl){
    //var TextInsideLi = ctrl.getElementsByTagName('p')[0].innerHTML;
}
///////////////////////////////////////////////////////////////////////////////////////////////////
function select_language() {
  var e = document.getElementById("ddlViewBy");
  var strUser = e.options[e.selectedIndex].text;
  if (strUser == "English") {
    window.location.href='lg/en/page_examining.html';
  } else if (strUser == "Romanian") {
      window.location.href='lg/ro/page_examining.html';
    }
}
