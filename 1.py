# # . Максимальная сумма подмассива длины k
# # Условие:
# # Дан массив nums и число k. Найдите максимальную сумму подмассива длины k.
# # Алгоритм: Sliding Window (фиксированное окно)
# # Подсказка:
# # Сначала посчитай сумму первых k, потом сдвигай окно.
#
#
# nums = [1, 4, 2, 10, 24, 3, 1, 0, 20]
# k = 3
#
#
# def max_sum_subarray(nums, k):
#     left = 0
#     current_sum = sum(nums[:k])
#     print(current_sum)
#     max_sum = current_sum
#     for right in range(k, len(nums)):
#         current_sum += nums[right] - nums[left]
#         max_sum = int(max(max_sum, current_sum) / k)
#         left += 1
#     return max_sum

# print(max_sum_subarray(nums, k))  # Output: 39


# 3. Самая длинная подстрока без повторяющихся символов
# Условие:
# Дана строка s. Найдите длину самой длинной подстроки без повторов.
# Алгоритм: Sliding Window + HashMap
# Подсказка:
# Если символ повторился — сдвигай left.

s = "Привет мир"


def long_string(s):
    left = 0  # левый край окна
    max_len = 0  # максимальная длина подстроки
    window = {}  # словарь для хранения символов и их последнего индекса

    for right in range(len(s)):
        char = s[right]
        # Если символ уже в окне и находится внутри текущего окна
        if char in window and window[char] >= left:
            left = window[char] + 1  # сдвигаем левый край окна вправо

        window[char] = right  # обновляем индекс символа
        max_len = max(max_len, right - left + 1)  # обновляем максимум

    return max_len


print(long_string(s))
