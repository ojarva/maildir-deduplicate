Maildir Deduplicate
===================

Deduplicates maildir contents using hardlinks. Assumes immutable files.

As long as processes delivering/reading messages do not change the contents, deduplication works without data corruption, and without any support from MTA/mail clients. Maildir specification mandates that files must be modified only under tmp directories. All other operations should be either creating hard links or unlinking. However, not all programs follow this principle.

Messages are deduplicated on file level (instead of block level), meaning, only exactly the same messages will be deduplicated.

There is no built-in mechanism to undo deduplication. If enough space is available, probably the easiest approach is to copy the whole maildir and delete the original one (and repeat this for all deduplicated directories). When finished, delete the `dedup` folder.


Installation
------------

No dependencies. Edit `settings.py` to add pattern for maildir folders.

Assumes `maildir` subfolder and creates `dedup` folder for storing hard links using hashes. For example, `FOLDERS = ["/storage/gmail/*"]` assumes following folder structure:


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
- Calculate SHA512 hash of file contents (everything, including headers). Convert hash to hexdigest.
- Create folder `dedup/hash[0]/hash[1]/hash[2]` to avoid folders with too many files.
- Check whether `dedup/hash[0]/hash[1]/hash[2]/hash` exists.
  - If yes, check whether both original file and hash file point to same inode.
    - If yes, skip.
    - If no, delete the original file and create a new hard link from the hash file to the original file.
  - If no, create new hard link from the original file to the hash filename.


TODO
----

Handle file deletion. Currently, if all copies of the message has been deleted, hard link under `dedup/` still persists. `os.stat` returns `st_nlink`, which is the number of hard links to inode. If `st_nlink` is >1, hash file is still in use.
