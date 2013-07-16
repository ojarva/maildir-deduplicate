Maildir Deduplicate
===================

Deduplicates maildir contents using hardlinks. Assumes immutable files. 

As long as processes delivering/reading messages do not change the contents, deduplication
works without data corruption, and without any support from MTA/mail clients. Maildir specification
mandates that files must be modified only under tmp directories. All other operations should be either
creating hard links or unlinking. However, not all programs follow this principle.

As no support from other programs is expected, even slightest differences between duplicate messages
causes deduplication process to leave messages untouched.

There's no easy way to undo deduplication. If the space permits, probably the easiest way is to
copy whole maildir folder and delete the original one.

Installation
------------

No dependencies. Edit settings.py to add pattern for maildir folders. 

Assumes "maildir" subfolder and creates "dedup" folder for storing hard links
using hashes. For example, 'FOLDERS = ["/storage/gmail/*"]' assumes following 
folder structure:

 /storage
  \- gmail
     \- something - write permission to this folder and everything under this is necessary
        \- maildir
           \- label
              \- cur
              \- new
              \- tmp - skipped
           \- label
              \- cur
              ...
           ...
        \- dedup - automatically created by maildir-dedup.py

Deduplication process goes as follows:

- Scan all files under cur/new folders. See maildir(5) for more information.
- Calculate SHA512 hash of file contents (everything, including headers)
- Create folder dedup/hash[0]/hash[1]/hash[2] to avoid folders with too many files
- Check whether dedup/hash[0]/hash[1]/hash[2]/hash exists.
   - If yes, check whether both original file and hash file point to same inode.
     - If yes, skip.
     - If no, delete original file and create new hard link from hash file to original file
   - If no, create new hard link from hash file to original file


TODO
----

Handle file deletion. Currently, if all copies of the message has been deleted,
hard link under dedup/ still persists. os.stat returns st_nlink, which returns number
of hard links to inode. If st_nlink is >1, hash file is still in use.
