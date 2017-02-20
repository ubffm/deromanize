Deromanize
==========
``deromanize`` is a set of tools to aid in converting Romanized text
back into original scripts.

.. contents::

``TransKey``
------------
TransKey is a class to help parse a profile which describes a
transliteration standard. The programmer still must define how the
contents of the profile data will be used, but the TransKey is a helpful
mechanism for simplifying this process.

Creating a Profile
~~~~~~~~~~~~~~~~~~
A profile has fairly simple format. It is a dictionary which contains
dictionaries with strings or lists of strings. It can easily be stored
as JSON, or a .ini file could be used with little post processing. I
like to use YAML because it's easy to write (though I do not mean to
endorse the abomination that is the YAML standard in so doing; Perhaps
hjson would be a saner choice).

The profile, at the very least, must define all consonants and vowels
used in the tranliteration standard (including digraphs).

.. code:: yaml
	  
    consonants:
	ʾ: א
	b: ב
	v: ב
	g: ג
	d: ד
	h: ה
	ṿ: [וו, ו]
	z: ז
	ḥ: ח
	ṭ: ט
	y: [יי, י]
	k: כ
	kh: כ
	l: ל
	m: מ
	n: נ
	s: ס
	ʿ: ע
	p: פ
	f: פ
	ts: צ
	ḳ: ק
	r: ר
	ś: ש
	sh: ש
	t: ת

    vowels:
	i: י
	e: ['', י]
	a: ''
	o: [ו, '']
	u: ו
