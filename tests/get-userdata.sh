#!/bin/bash -ex

ec2 get-userdata - | grep '#!/bin/bash'
ec2 get-userdata userdata.txt
[ -r userdata.txt ] && grep '#!/bin/bash' userdata.txt && rm userdata.txt