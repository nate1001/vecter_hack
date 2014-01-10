
clean:
	(cd model ; $(MAKE) clean )
	(cd view ; $(MAKE) clean )
	(cd controller ; $(MAKE) clean )
	rm *.pyc
