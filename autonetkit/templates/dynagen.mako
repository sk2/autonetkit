autostart = False
version = 0.8.3.1
[${topology.hypervisor_server}:${topology.hypervisor_port}]
    workingdir = /tmp
    udp = 10000
    [[2621]]
        image = ${topology.image}
        idlepc = 0x80397f88
        ghostios = True
        chassis = 2621

    %for router in topology.routers:
        [[ROUTER ${router.hostname}]]
        model = ${router.model}
        console = ${router.console}
        aux = ${router.aux}
        slot1 = NM-1FE-TX
        % for interface in router.interfaces:
        ${interface['src_port']} = ${interface['dst']} ${interface['dst_port']}
        %endfor
        x = ${router.x}
        y = ${router.y}
        z = 1.0
        cnfg = ${router.cnfg}
    %endfor

[GNS3-DATA]
    configs = configs

