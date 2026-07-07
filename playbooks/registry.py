PLAYBOOKS = {

    # =====================================================
    # Windows Services
    # =====================================================

    "service.info": {

        "name": "Windows Service",

        "collector": "windows_service",

        "metrics": [

            "service.info",      # Triggered service
            "system.cpu.util",
            "vm.memory.util",
            "vfs.fs.size",
            "system.uptime",
            "agent.ping"

        ]

    },

    # =====================================================
    # CPU
    # =====================================================

    "system.cpu.util": {

        "name": "CPU",

        "collector": "cpu",

        "metrics": [

            "system.cpu.util",
            "system.cpu.load",
            "system.cpu.num",
            "vm.memory.util",
            "system.uptime"

        ]

    },

    # =====================================================
    # Memory
    # =====================================================

    "vm.memory.util": {

        "name": "Memory",

        "collector": "memory",

        "metrics": [

            "vm.memory.util",
            "vm.memory.size",
            "system.cpu.util",
            "system.uptime"

        ]

    },

    # =====================================================
    # Disk Usage
    # =====================================================

    "vfs.fs.size": {

        "name": "Disk",

        "collector": "disk",

        "metrics": [

            "vfs.fs.size",
            "system.cpu.util",
            "vm.memory.util",
            "system.uptime"

        ]

    },

    # =====================================================
    # Filesystem
    # =====================================================

    "vfs.fs.dependent": {

        "name": "Filesystem",

        "collector": "filesystem",

        "metrics": [

            "vfs.fs.dependent",
            "vfs.fs.size",
            "system.cpu.util",
            "vm.memory.util"

        ]

    },

    # =====================================================
    # Filesystem Inodes
    # =====================================================

    "vfs.fs.dependent.inode": {

        "name": "Filesystem Inode",

        "collector": "filesystem",

        "metrics": [

            "vfs.fs.dependent.inode",
            "vfs.fs.size",
            "system.cpu.util",
            "vm.memory.util"

        ]

    },

    # =====================================================
    # Redis
    # =====================================================

    "redis.ping": {

        "name": "Redis",

        "collector": "redis",

        "metrics": [

            "redis.ping",
            "system.cpu.util",
            "vm.memory.util",
            "agent.ping"

        ]

    },

    # =====================================================
    # Network
    # =====================================================

    "net.tcp.service": {

        "name": "Network",

        "collector": "network",

        "metrics": [

            "net.tcp.service",
            "system.cpu.util",
            "vm.memory.util",
            "agent.ping"

        ]

    },

    # =====================================================
    # Zabbix Agent
    # =====================================================

    "agent.ping": {

        "name": "Zabbix Agent",

        "collector": "agent",

        "metrics": [

            "agent.ping",
            "system.cpu.util",
            "vm.memory.util",
            "system.uptime"

        ]

    }

}