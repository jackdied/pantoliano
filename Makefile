

hackfest:
	rm -f log
	touch log
	cat strace.log | python pantoliano.py
