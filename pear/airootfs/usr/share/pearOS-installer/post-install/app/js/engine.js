function list_zones() {
//vars:
const { exec } = require('child_process');
count = 0;
i = 1 ;
var z=``;
var fullName='';

exec('find /usr/share/zoneinfo/posix -type f -or -type l | sort | cut -c27- | wc -l', (err, zone_count) => {
var sZones = `${zone_count}`
zones_count = parseInt(sZones);
console.log("There are " + zones_count + " available time-zones");

while (i < (zones_count+1)) {
	exec("find /usr/share/zoneinfo/posix -type f -or -type l | sort | cut -c27- | sed -n "+ i  + "p", (err, stdout) => { var zi=`<option>${stdout}</option>`; i++; z += zi; document.getElementById("time_zones_list").innerHTML =z; })
        i++;
        }
	})
}
function select_language() {
  var e = document.getElementById("ddlViewBy");
  if (e.options[e.selectedIndex] === undefined) { alert('You must choose one Language from the list'); } else {
  var strUser = e.options[e.selectedIndex].text;
  const fs = require('fs');
  if (strUser == "Chinese (Simplified)") {
      fs.writeFileSync('/tmp/locale', 'zh_CN.UTF-8');
    window.location.href='lg/zn_CN/page_keymap.html';
  } else if (strUser == "English (Australia)") {
      fs.writeFileSync('/tmp/locale', 'en_AU.UTF-8');
      window.location.href='lg/en_AU/page_keymap.html';
    } else if (strUser == "English (Canada)") {
        fs.writeFileSync('/tmp/locale', 'en_CA.UTF-8');
      window.location.href='lg/en_CA/page_keymap.html';
      } else if (strUser == "English (United States)") {
          fs.writeFileSync('/tmp/locale', 'en_USS.UTF-8');
        window.location.href='lg/en_US/page_keymap.html';
        } else if (strUser == "English (United Kingdom)") {
            fs.writeFileSync('/tmp/locale', 'en_GB.UTF-8');
            window.location.href='lg/en_GB/page_keymap.html';
          } else if (strUser == "French (France)") {
              fs.writeFileSync('/tmp/locale', 'fr_FR.UTF-8');
              window.location.href='lg/fr_FR/page_keymap.html';
            } else if (strUser == "German (Germany)") {
                fs.writeFileSync('/tmp/locale', 'de_DE.UTF-8');
                window.location.href='lg/de_DE/page_keymap.html';
              } else if (strUser == "Italian (Italy)") {
                  fs.writeFileSync('/tmp/locale', 'it_IT.UTF-8');
                  window.location.href='lg/it_IT/page_keymap.html';
                }  else if (strUser == "Japanese (Japan)") {
                    fs.writeFileSync('/tmp/locale', 'ja_JP.UTF-8');
                     window.location.href='lg/ja_JP/page_keymap.html';
                  }  else if (strUser == "Portuguese (Brazil)") {
                      fs.writeFileSync('/tmp/locale', 'pt_BR.UTF-8');
                         window.location.href='lg/pt_BR/page_keymap.html';
                    } else if (strUser == "Portuguese (Portugal)") {
                        fs.writeFileSync('/tmp/locale', 'pt_PT.UTF-8');
                           window.location.href='lg/pt_PT/page_keymap.html';
                      } else if (strUser == "Russian (Russia)") {
                          fs.writeFileSync('/tmp/locale', 'ru_RU.UTF-8');
                             window.location.href='lg/ru_RU/page_keymap.html';
                        } else if (strUser == "Romanian (Romania)") {
                            fs.writeFileSync('/tmp/locale', 'ro_RO.UTF-8');
                               window.location.href='lg/ro_RO/page_keymap.html';
                          } else if (strUser == "Spanish (Mexico)") {
                              fs.writeFileSync('/tmp/locale', 'es_MX.UTF-8');
                                 window.location.href='lg/es_MX/page_keymap.html';
                            } else if (strUser == "Spanish (Spain)") {
                                fs.writeFileSync('/tmp/locale', 'es_ES.UTF-8');
                                   window.location.href='lg/es_ES/page_keymap.html';
                              } else if (strUser == "Swedish (Sweden)") {
                                  fs.writeFileSync('/tmp/locale', 'sv_SE.UTF-8');
                                     window.location.href='lg/sv_SE/page_keymap.html';
                                } else if (strUser == '') {
                                    alert('You must select one language from the list');
                                }
  }
}

function select_keymap() {
  var e = document.getElementById("keymapList");
   if (e.options[e.selectedIndex] === undefined) { alert('You must choose one Keyboard Layout from the list'); } else {
  var strUser = e.options[e.selectedIndex].text;
  const fs = require('fs');
  if (strUser == "French") {
    fs.writeFileSync('/tmp/keymap', 'fr');
  } else if (strUser == "German") {
      fs.writeFileSync('/tmp/keymap', 'de');
      window.location.href='page_timezone.html';
    } else if (strUser == "Greek") {
      fs.writeFileSync('/tmp/keymap', 'gr');
      window.location.href='page_timezone.html';
      } else if (strUser == "Hungarian") {
        fs.writeFileSync('/tmp/keymap', 'hu');
        window.location.href='page_timezone.html';
        } else if (strUser == "Italian") {
            fs.writeFileSync('/tmp/keymap', 'it');
            window.location.href='page_timezone.html';
          } else if (strUser == "Polish") {
              fs.writeFileSync('/tmp/keymap', 'pl');
              window.location.href='page_timezone.html';
            } else if (strUser == "Russian") {
                fs.writeFileSync('/tmp/keymap', 'ru');
                window.location.href='page_timezone.html';
              } else if (strUser == "Spanish") {
                  fs.writeFileSync('/tmp/keymap', 'es');
                  window.location.href='page_timezone.html';
                }  else if (strUser == "United States") {
                     fs.writeFileSync('/tmp/keymap', 'us');
                     window.location.href='page_timezone.html';
                  }
   }
}

function select_timezone() {
  var e = document.getElementById("time_zones_list");
   if (e.options[e.selectedIndex] === undefined) { alert('You must choose one Time Zone from the list'); } else {
       var strUser = e.options[e.selectedIndex].text;
       const fs = require('fs');
        fs.writeFileSync('/tmp/timezone', '' + strUser);
        window.location.href='page_user.html';
   }
}

function save_user(){
	fullName = document.getElementById("full_name").value;
	var userName = document.getElementById("account_name").value;
	var password = document.getElementById("password").value;
	var password_confirm = document.getElementById("password_confirm").value;
	const regex = /^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$/g
	const checkgex = userName.match(regex);
	const fs = require('fs');

    if(fullName == '') { alert("FullName cannot be empty"); } else { fs.writeFileSync('/tmp/fullname', `'` + fullName + `'`); };
    if(userName == '') { alert("Username cannot be empty"); } else { console.log("Username not empty. Continuing!");};
    if(password == '') { alert("Password cannot be empty"); } else if(password != '') { check_match();}
}

function check_match(){
  fullName = document.getElementById("full_name").value;
  var userName = document.getElementById("account_name").value;
  var password = document.getElementById("password").value;
  var password_confirm = document.getElementById("password_confirm").value;
  const regex = /^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$/g
  const checkgex = userName.match(regex);

  if( password != password_confirm) {
    alert("Passwords are not matching!");
  } else {
	checkchars();
    }
}

function checkchars() {
	var userName = document.getElementById("account_name").value;
	const regex = /^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$/g
	const checkgex = userName.match(regex);

	var password = document.getElementById("password").value;

	if(checkgex == null) {
  	alert("The username you inputed contains illegal characters. The username needs to check the following:\n - start with a lowercase (i.e.: alex)\n - does not start with a number (i.e.: 8alex8)\n - does not start with a character (i.e. -_alex_-)");
	} else {
	const fs = require('fs');
      	if(fullName == '') { alert("FullName cannot be empty"); } else { fs.writeFileSync('/tmp/fullname', `'` + fullName + `'`); };
	if(userName == '' || checkgex == null) { alert("username cannot be empty"); } else { fs.writeFileSync('/tmp/username', '' + userName); };
	fs.writeFileSync('/tmp/password', '' + password);
	window.location.href='page_agreement.html';
  }
}

function commit(){
  var fs = require('fs');

    fs.readFile('/tmp/fullname', 'utf-8', (err, fn_data) => { var fullname = fn_data; fs.readFile('/tmp/username', 'utf-8', (err, usr_data) => { var username = usr_data; fs.readFile('/tmp/password', 'utf-8', (err, passwd_data) => { var password = passwd_data; fs.readFile('/tmp/keymap', 'utf-8', (err, kmap_data) => { var keymap = kmap_data; fs.readFile('/tmp/locale', 'utf-8', (err, locale_data) => { var locale = locale_data; fs.readFile('/tmp/timezone', 'utf-8', (err, tzone_data) => { var timezone = tzone_data; const { exec } = require('child_process'); const execSync = require("child_process").execSync;
        console.log('Keymap is ' + keymap);
        console.log('Locale is ' + locale);
        console.log('Timezone is ' + timezone);
        console.log('');
        console.log('User passowrd is ' + password);
        console.log('User Full name is ' + fullname);
        console.log('username is ' + username);
        // Comment the above line if you want to enable the debugger mode (must uncomment the line above this).
        execSync("sudo post_setup " + keymap + ' ' + locale + ' ' + timezone + ' ' + password + ' ' + fullname + ' ' + username, (err, stdout) => { console.log(stdout); });
	window.exit();
        // Uncomment the above line if you want to enable the debugger mode. It will print the selected stuff in the Developer Tools Console (inspect element).
        //execSync("post_setup " + keymap + ' ' + locale + ' ' + timezone + ' ' + password + ' ' + fullname + ' ' + username + ' ' + 'debug', (err, stdout) => { console.log(stdout); });
    }) })})});}); });
}
