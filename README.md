spindl
======

all your disc are belong to us

# sketch of flow

```console
get tags from file
if no tags
	CONTINUE

if file in s3
	if MYNAME-TAGGED.type.md5sum matches thisfile.type.md5sum
		this file is good
		CONTINUE
	convert file to clean, tag-free wave
	get md5sum
	compare wave md5sum to s3
	if bad
		IF NOT FS-READ-ONLY
			DOWNLOAD FILE
			turn golden master into silver master
	else
		this file is good
		IF NOT S3-READ-ONLY
			set s3 metadata for {this}.md5sum
			set MYNAME-TAGGED.alac.md5sum to (post-tagging) md5
	CONTINUE
else (it's not in s3)
	IF S3-READ-ONLY
		CONTINUE
	if it's not wave
		ADD TO TAGS: SOURCE WAS "FLAC/ALAC/MP3/M4A/OGG"
	convert to master wave (no tags)
	get md5sum (master wave)

	turn wave into gold master:
		convert to flac (no tags)
		convert to wave (no tags)
		confirm that flac->wave md5 matches master md5
		if not
			BOGUS ENCODER
		now we have clean wave/md5, flac/md5
		analyze flac
		gzip analysis file
		upload analysis file
		gzip adjacent log file
		upload adjacent log file
		(these are sources with no tags in them)
		upload flac to s3
		confirm md5, set flac md5
		set wave md5 just for kicks
	turn gold master into silver master

turn gold master into silver master:
	if --output={format}
		convert to {format} (if necessary)
		get md5sum ({format}) (if necessary)
		write tags here
		convert to wave
		get md5sum (wave)
		if md5sum is okay
			IF NOT S3-READ-ONLY
				set {format} md5 at s3 (pre-tagging)
				set MYNAME-TAGGED.{format}.md5sum to (post-tagging) md5
		else
			BOGUS ENCODER OR TAGGER
			RETURN
		IF NOT FS-READ-ONLY
			write silver master (perhaps over original file)
			delete original file if it had a different type
```
