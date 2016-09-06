#! /bin/bash
#
# BASH script to update /etc/ssh/sshd_config in
# compute nodes to prevent users' direct access

sed -i '/Block/d' /etc/ssh/sshd_config
sed -i '/Subsystem/a# Block hpc-users' /etc/ssh/sshd_config
sed -i '/Block hpc-users/{x;p;x;}' /etc/ssh/sshd_config
sed -i '/DenyGroups/d' /etc/ssh/sshd_config
sed -i '/Block hpc-users/aDenyGroups bio1 bio2 freshman' /etc/ssh/sshd_config
