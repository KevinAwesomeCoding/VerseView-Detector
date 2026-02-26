# VerseView-Detector
If you have a Intel Mac, follow these steps:

Step 1: Install the Mac audio tools
Copy and paste this command and hit Enter (it might ask for their Mac password):

Bash

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
When that finishes, copy and paste this and hit Enter:

Bash

brew install portaudio

Step 2: Set up the project folder
Type cd  (make sure there is a space after "cd").

Drag and drop the unzipped project folder directly into the Terminal window and hit Enter.

Run this command to create a safe workspace:

Bash

python3 -m venv venv

Turn the workspace on:

Bash

source venv/bin/activate
(They should see (venv) pop up on the left side of their terminal).

Step 3: Install the requirements
Copy and paste these two commands, hitting Enter after each:

Bash

pip install -r requirements.txt

Bash

pip install pyinstaller
Step 4: Build the App!

Run this final command:

Bash

pyinstaller verseview.spec

