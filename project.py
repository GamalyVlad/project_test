import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from typing import List, Dict

class OrderBlockVisualizer:
    def __init__(self, ticker: str, start_date: str, end_date: str, range_len: int = 15):
        """
        Ініціалізує об'єкт OrderBlockVisualizer з наданими параметрами.

        :param ticker: Тікер акцій для завантаження даних
        :param start_date: Початкова дата для завантаження даних
        :param end_date: Кінцева дата для завантаження даних
        :param range_len: Довжина діапазону для розрахунків структури (за замовчуванням 15)
        """
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.range_len = range_len
        self.data = self._download_data()
        self.short_boxes = []
        self.long_boxes = []
        self.bos_lines = []
        self._init_variables()
        
    def _download_data(self) -> pd.DataFrame:
        """
        Завантажує дані для вказаного тікеру та діапазону дат.

        :return: DataFrame з історичними даними акцій
        """
        return yf.download(self.ticker, start=self.start_date, end=self.end_date)
    
    def _init_variables(self):
        """
        Ініціалізує змінні для зберігання даних про свічки.
        """
        self.lastDownIndex = 0
        self.lastDown = 0
        self.lastLow = 0
        self.lastUpIndex = 0
        self.lastUp = 0
        self.lastUpLow = 0
        self.lastUpOpen = 0
        self.lastHigh = 0
        self.structureLowIndex = 0
        self.structureLow = 1000000
        self.lastLongIndex = 0
        self.lastShortIndex = 0
    
    def structureLowIndexPointer(self) -> List[int]:
        """
        Визначає індекси структурних мінімумів.

        :return: Список індексів структурних мінімумів
        """
        minValue = self.data['High'].rolling(window=self.range_len).max().shift(1)
        minIndex = list(range(len(self.data)))
        for i in range(1, self.range_len):
            if self.data['Low'][i] < minValue[i]:
                minValue[i] = self.data['Low'][i]
                minIndex[i] = i
        return minIndex
    
    def calculate_structure_low(self):
        """
        Розраховує структуру низьких значень та їх індекси.
        """
        self.structureLow = self.data['Low'].rolling(window=self.range_len).min().shift(1)
        self.structureLowIndex = self.structureLowIndexPointer()
    
    def add_order_block(self, index: int, top: float, bottom: float, color: str) -> Dict[str, float]:
        """
        Додає блок замовлень з вказаними параметрами.

        :param index: Індекс початку блоку
        :param top: Верхня межа блоку
        :param bottom: Нижня межа блоку
        :param color: Колір блоку
        :return: Словник з параметрами блоку
        """
        return {
            "left": index,
            "top": top,
            "bottom": bottom,
            "right": len(self.data) - 1,
            "color": color
        }
    
    def process_order_blocks(self):
        """
        Обробляє блоки замовлень та лінії BOS.
        """
        for i in range(len(self.data)):
            if self.data['Low'][i] < self.structureLow[i]:
                if i - self.lastUpIndex < 1000:
                    self.short_boxes.append(self.add_order_block(self.lastUpIndex, self.lastHigh, self.lastUpLow, 'rgba(255,0,0,0.9)'))
                    if True:  # showBearishBOS
                        self.bos_lines.append(self.add_order_block(self.structureLowIndex[i], self.structureLow[i], self.structureLow[i], 'red'))
                self.lastShortIndex = self.lastUpIndex

            if len(self.short_boxes) > 0:
                for box in self.short_boxes:
                    if self.data['Close'][i] > box['top']:
                        self.short_boxes.remove(box)
                        if i - self.lastDownIndex < 1000 and i > self.lastLongIndex:
                            self.long_boxes.append(self.add_order_block(self.lastDownIndex, self.lastDown, self.lastLow, 'rgba(0,255,0,0.9)'))
                            if True:  # showBullishBOS
                                self.bos_lines.append(self.add_order_block(box['left'], box['top'], box['top'], 'green'))
                            self.lastLongIndex = i

            if len(self.long_boxes) > 0:
                for box in self.long_boxes:
                    if self.data['Close'][i] < box['bottom']:
                        self.long_boxes.remove(box)

            # Запис останніх свічок
            if self.data['Close'][i] < self.data['Open'][i]:
                self.lastDown = self.data['High'][i]
                self.lastDownIndex = i
                self.lastLow = self.data['Low'][i]

            if self.data['Close'][i] > self.data['Open'][i]:
                self.lastUp = self.data['Close'][i]
                self.lastUpIndex = i
                self.lastUpOpen = self.data['Open'][i]
                self.lastUpLow = self.data['Low'][i]
                self.lastHigh = self.data['High'][i]

            # Оновлення останніх high/low для точніших блоків замовлень
            self.lastHigh = max(self.lastHigh, self.data['High'][i])
            self.lastLow = min(self.lastLow, self.data['Low'][i])
    
    def calculate_pdh_pdl(self):
        """
        Розраховує значення попереднього дня високого (PDH) та низького (PDL).
        """
        self.pdh = self.data['High'][-2]  # Попередній день високий
        self.pdl = self.data['Low'][-2]   # Попередній день низький
    
    def visualize(self):
        """
        Створює та відображає графік з блоками замовлень та лініями BOS.
        """
        fig = go.Figure()

        # Додавання свічок
        fig.add_trace(go.Candlestick(
            x=self.data.index,
            open=self.data['Open'],
            high=self.data['High'],
            low=self.data['Low'],
            close=self.data['Close'],
            name='Candlesticks',
            showlegend=False
        ))

        # Додавання блоків замовлень до графіку
        for box in self.short_boxes:
            left_index = box['left']
            right_index = min(box['right'], len(self.data) - 1)
            fig.add_trace(go.Scatter(
                x=[self.data.index[left_index], self.data.index[right_index], self.data.index[right_index], self.data.index[left_index], self.data.index[left_index]],
                y=[box['top'], box['top'], box['bottom'], box['bottom'], box['top']],
                fill='toself',
                fillcolor=box['color'],
                line=dict(color=box['color']),
                mode='lines',
                showlegend=False
            ))

        for box in self.long_boxes:
            left_index = box['left']
            right_index = min(box['right'], len(self.data) - 1)
            fig.add_trace(go.Scatter(
                x=[self.data.index[left_index], self.data.index[right_index], self.data.index[right_index], self.data.index[left_index], self.data.index[left_index]],
                y=[box['top'], box['top'], box['bottom'], box['bottom'], box['top']],
                fill='toself',
                fillcolor=box['color'],
                line=dict(color=box['color']),
                mode='lines',
                showlegend=False
            ))

        # Додавання ліній BOS до графіку
        for line in self.bos_lines:
            left_index = line['left']
            right_index = min(line['right'], len(self.data) - 1)
            fig.add_trace(go.Scatter(
                x=[self.data.index[left_index], self.data.index[right_index]],
                y=[line['top'], line['bottom']],
                mode='lines',
                line=dict(color=line['color']),
                showlegend=False
            ))

        # Додавання горизонтальних ліній PDL та PDH
        fig.add_trace(go.Scatter(
            x=[self.data.index[0], self.data.index[-1]],
            y=[self.pdh, self.pdh],
            mode='lines',
            line=dict(color='blue', dash='dash'),
            name='PDH'
        ))

        fig.add_trace(go.Scatter(
            x=[self.data.index[0], self.data.index[-1]],
            y=[self.pdl, self.pdl],
            mode='lines',
            line=dict(color='orange', dash='dash'),
            name='PDL'
        ))

        # Налаштування оформлення графіку
        fig.update_layout(title=f'{self.ticker} Order Blocks and BOS',
                          xaxis_title='Date',
                          yaxis_title='Price',
                          template='plotly_dark')

        fig.show()

# Використання класу
obv = OrderBlockVisualizer(ticker='AAPL', start_date='2024-01-01', end_date='2025-01-01')
obv.calculate_structure_low()
obv.process_order_blocks()
obv.calculate_pdh_pdl()
obv.visualize()
