#!/bin/bash
#set -e

#DemonKiller's Git Commit Script
#Repo must be cloned to local for this to work


# checking if I have the latest files from github
tput setaf 4
echo "Checking for newer files online first"
tput sgr0
git pull


# Below command will backup everything inside the project folder
git add --all .

# Give a comment to the commit if you want
tput setaf 1
echo "Write Commit Below:"
tput sgr0

read input

# Committing to the local repository with a message containing the time details and commit text

git commit -m "$input"

# Push the local files to github

git push

tput setaf 2
echo "D O N E!"
tput sgr0
