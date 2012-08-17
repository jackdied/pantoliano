

hackfest:
	rm -f log
	touch log
	cat strace.log | python straxe.py
