

clean:
	(cd model ; $(MAKE) clean )
	(cd view ; $(MAKE) clean )
	(cd controller ; $(MAKE) clean )
	rm *.pyc

test_mains:
	$(MAKE) -C model test_mains
