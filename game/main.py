# Ponto de entrada do pygbag (o pygbag procura um main.py na pasta do jogo).
# O pygbag só detecta dependências lendo ESTE arquivo, por isso o import
# explícito de pygame aqui (sem ele o pygame não é carregado no navegador).
import asyncio

import pygame  # noqa: F401

import soccer

asyncio.run(soccer.main())
