"""
Maildir deduplication using hard links. Assumes immutable messages.

"""

import glob
import hashlib
import logging
import logging.handlers
import os
import os.path
import sys
import time


class MaildirDedup:

    def __init__(self, folder, **kwargs):
        self.folder = folder

        self.logger = logging.getLogger(f"maildirdedup - {self.folder}")
        self.logger.setLevel("INFO")
        if kwargs.get("syslog", True):
            handler = logging.handlers.SysLogHandler(address='/dev/log')
        else:
            handler = logging.StreamHandler()

        formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.stats = {}
        self.finished = False
        if not os.path.exists(self.folder):
            self.logger.error("No such folder")
            raise IOError(f"No such folder: {self.folder}")

    @staticmethod
    def calchash(filename):
        """Calculate file hash memory-efficiently"""
        ahash = hashlib.sha512()
        with open(filename) as afile:
            while True:
                data = afile.read(8192)
                if not data:
                    break
                ahash.update(data)
        digest = ahash.hexdigest()
        folder = f"{digest[0]}/{digest[1]}/{digest[2]}"
        return (folder, digest)

    @staticmethod
    def dedupfile(filename, dedupfolder, stats=None, last_timestamp=0):
        if stats is None:
            stats = {}
        file_stat = os.stat(filename)
        if file_stat.st_mtime < last_timestamp:
            stats["mtime_skipped"] += 1
            return
        dedupf, ahash = MaildirDedup.calchash(filename)
        dedupfile = f"{dedupfolder}/{dedupf}/{ahash}"
        try:
            os.makedirs(f"{dedupfolder}/{dedupf}")
        except OSError:
            pass
        if os.path.exists(dedupfile):
            if os.stat(dedupfile).st_ino == file_stat.st_ino:
                stats["already"] += 1
                return
            stats["new"] += 1
            os.remove(filename)
            os.link(dedupfile, filename)
        else:
            stats["dedup"] += 1
            os.link(filename, dedupfile)

    def run(self):
        self.logger.info("Starting")
        folder = self.folder

        if not os.path.exists(f"{folder}/maildir"):
            self.logger.error("No such directory: %s/maildir", folder)
            return
        dedupfolder = f"{folder}/dedup"
        stats = {"new": 0, "dedup": 0, "already": 0, "mtime_skipped": 0}

        if not os.path.exists(dedupfolder):
            os.mkdir(dedupfolder)

        try:
            with open(f"{dedupfolder}/last_timestamp") as timestamp_file:
                last_timestamp = float(timestamp_file.read()) - 3600
        except (IOError, EOFError):
            last_timestamp = 0

        def process_folder(afolder):
            folder_stat = os.stat(afolder)
            if folder_stat.st_mtime < last_timestamp:
                self.logger.debug("Skipping %s: no modifications since %s", afolder, last_timestamp)
                return

            for afile in glob.glob(f"{afolder}/*"):  # "imap folder / {cur,new,tmp} / file"
                MaildirDedup.dedupfile(afile, dedupfolder, stats, last_timestamp)

        # Only process cur/new folders under maildirs. tmp is messages still being processed / not completed.
        # There's a risk files under tmp are still being modified.
        for afolder in glob.glob(f"{folder}/maildir/*/cur"):  # "imap folder / cur"
            process_folder(afolder)

        for afolder in glob.glob(f"{folder}/maildir/*/new"):  # "imap folder / new"
            process_folder(afolder)

        last_timestamp = time.time()
        with open(f"{dedupfolder}/last_timestamp", "w") as outfile:
            outfile.write(str(last_timestamp))
        self.stats = stats
        self.finished = True
        self.logger.info("Finished. %s files deduplicated.", stats["dedup"])
        return stats


def usage():
    print("""
usage: %s <maildir folder> [<more folders>]

or create settings.py file with

'FOLDERS=[...]'
""" % sys.argv[0])


def main(folders):
    if len(folders) == 0:
        usage()
        return 1

    stats_all = {}
    for main_folder in folders:
        for subfolder in glob.glob(main_folder):
            maildirdedup = MaildirDedup(subfolder)
            stats = maildirdedup.run()
            if stats:
                for key in stats:
                    if key not in stats_all:
                        stats_all[key] = 0
                    stats_all[key] += stats[key]
    return 0


def get_folders():
    # If folders given as command line arguments, use those. If not, try settings.py.
    if len(sys.argv) > 1:
        folders = sys.argv[1:]
    else:
        try:
            from settings import FOLDERS as folders
        except ImportError:
            folders = []
    return folders

if __name__ == '__main__':
    FOLDERS = get_folders()
    sys.exit(main(FOLDERS))
