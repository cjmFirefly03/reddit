# Verification Bot
Originally forked from https://github.com/captainmeta4/PlusBot
##Usage
Parameter | Short Name | Type | Description
--- | --- | --- | ---
--post-id | -p | string | Reddit Post Id (required)
--records-wiki | -rw | string | Base Wiki Page (required)
--add-comment | -ac | boolean | If true, add comments to the post to give user feedback.
--detect-dups | -dd | boolean | If true, skip replies that have been previously processed. (default: true)
--force-flair-update | -ff | boolean | If true, bot will update all flair. If false, bot only updates modified ones. (default: false)
--force-flair-wiki | -fw | boolean | If true, bot will update all record pages - WARNING: this could take a while. If false, bot only updates modified ones. (default: false)
--pickle-file | -pf | string | Name of pickle file to use as db (ex. original_records)
```
python wrapper.py -p 81cu0t 7tr7ud -rw records
```
C:\Python27\python.exe wrapper.py -p 89az64 -rw records

C:\Python27\python.exe wrapper.py -p 93x94h 8wuypf -rw records

C:\Python27\python.exe wrapper.py -p 8gfi2n -rw records -dd False -pf original_records_05_09_18
