

hackfest:
	rm log
	touch log
	cat strace.log | python straxe.py
