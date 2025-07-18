#!/bin/bash
echo "Taking VNC screenshot to check current state..."
vnccapture -H localhost -P test123 -o /mnt/c/Users/danhc/Downloads/vnc_test_mesa.png
echo "Screenshot saved to /mnt/c/Users/danhc/Downloads/vnc_test_mesa.png"